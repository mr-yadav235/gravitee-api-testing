/**
 * Unit Tests for Gravitee API Policies
 * Tests policy configurations and transformations
 */

const yaml = require('js-yaml');
const fs = require('fs');
const path = require('path');

describe('API Policy Unit Tests', () => {
  let apiDefinition;

  beforeAll(() => {
    // Load API definition
    const apiPath = process.env.API_DEFINITION_PATH || 
      path.join(__dirname, '../../gko/crds/api-definition-v4.yaml');
    const content = fs.readFileSync(apiPath, 'utf8');
    apiDefinition = yaml.load(content);
  });

  describe('Rate Limiting Policy', () => {
    test('should have rate limiting configured', () => {
      const flows = apiDefinition.spec.flows || [];
      const rateLimitPolicy = flows
        .flatMap(f => f.request || [])
        .find(p => p.policy === 'rate-limit');
      
      expect(rateLimitPolicy).toBeDefined();
      expect(rateLimitPolicy.enabled).toBe(true);
    });

    test('rate limit should be within acceptable range', () => {
      const flows = apiDefinition.spec.flows || [];
      const rateLimitPolicy = flows
        .flatMap(f => f.request || [])
        .find(p => p.policy === 'rate-limit');
      
      if (rateLimitPolicy) {
        const limit = rateLimitPolicy.configuration.rate.limit;
        expect(limit).toBeGreaterThan(0);
        expect(limit).toBeLessThanOrEqual(10000);
      }
    });
  });

  describe('Transform Headers Policy', () => {
    test('should add transaction ID header', () => {
      const flows = apiDefinition.spec.flows || [];
      const transformPolicy = flows
        .flatMap(f => f.request || [])
        .find(p => p.policy === 'transform-headers');
      
      expect(transformPolicy).toBeDefined();
      
      const headers = transformPolicy.configuration.addHeaders || [];
      const transactionHeader = headers.find(h => 
        h.name === 'X-Gravitee-Transaction-Id' || 
        h.name === 'X-Request-Id'
      );
      
      expect(transactionHeader).toBeDefined();
    });

    test('should not expose sensitive headers', () => {
      const flows = apiDefinition.spec.flows || [];
      const transformPolicies = flows
        .flatMap(f => [...(f.request || []), ...(f.response || [])])
        .filter(p => p.policy === 'transform-headers');
      
      const sensitiveHeaders = [
        'X-Internal-Token',
        'X-Database-Password',
        'X-Secret-Key'
      ];
      
      transformPolicies.forEach(policy => {
        const headers = policy.configuration.addHeaders || [];
        headers.forEach(h => {
          expect(sensitiveHeaders).not.toContain(h.name);
        });
      });
    });
  });

  describe('Security Plan Configuration', () => {
    test('should have at least one security plan', () => {
      const plans = apiDefinition.spec.plans || {};
      expect(Object.keys(plans).length).toBeGreaterThan(0);
    });

    test('JWT plan should have valid configuration', () => {
      const plans = apiDefinition.spec.plans || {};
      const jwtPlan = Object.values(plans).find(p => 
        p.security?.type === 'JWT'
      );
      
      if (jwtPlan) {
        expect(jwtPlan.security.configuration.signature).toBeDefined();
        expect(jwtPlan.security.configuration.publicKeyResolver).toBeDefined();
        expect(jwtPlan.status).toBe('PUBLISHED');
      }
    });

    test('should not have keyless plan in production configs', () => {
      const env = process.env.ENVIRONMENT || 'dev';
      const plans = apiDefinition.spec.plans || {};
      
      if (env === 'prod') {
        const keylessPlan = Object.values(plans).find(p => 
          p.security?.type === 'KEY_LESS' && p.status === 'PUBLISHED'
        );
        expect(keylessPlan).toBeUndefined();
      }
    });
  });

  describe('Endpoint Configuration', () => {
    test('should have valid backend URL', () => {
      const endpoints = apiDefinition.spec.endpointGroups?.[0]?.endpoints || [];
      expect(endpoints.length).toBeGreaterThan(0);
      
      endpoints.forEach(endpoint => {
        expect(endpoint.target).toMatch(/^https?:\/\/.+/);
      });
    });

    test('should have reasonable timeouts', () => {
      const endpoints = apiDefinition.spec.endpointGroups?.[0]?.endpoints || [];
      
      endpoints.forEach(endpoint => {
        const config = endpoint.configuration || {};
        if (config.connectTimeout) {
          expect(config.connectTimeout).toBeLessThanOrEqual(30000);
        }
        if (config.readTimeout) {
          expect(config.readTimeout).toBeLessThanOrEqual(60000);
        }
      });
    });
  });

  describe('Analytics Configuration', () => {
    test('analytics should be enabled', () => {
      expect(apiDefinition.spec.analytics?.enabled).toBe(true);
    });

    test('should not log payloads in production', () => {
      const env = process.env.ENVIRONMENT || 'dev';
      
      if (env === 'prod') {
        expect(apiDefinition.spec.analytics?.logging?.content?.payload).toBe(false);
      }
    });
  });
});

// Export for use in other test files
module.exports = { loadApiDefinition: (path) => yaml.load(fs.readFileSync(path, 'utf8')) };

