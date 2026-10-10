import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectGraphqlEnvelope } from './graphql-envelope.mjs';

const options = { allowedOrigin: 'https://studio.example.test', allowedOperations: ['GuidedFactCheckPrepare', 'GuidedFactCheckSubmit'] };
const request = (body, url = 'https://studio.example.test/api/graphql?secret=SECRET_URL') => ({
  method: 'Network.requestWillBeSent', sequence: 3,
  params: { timestamp: 10.2, request: { method: 'POST', url, hasPostData: true, ...(body === undefined ? {} : { postData: body }) } },
});

test('allowed operation is linked without query, variables, extension or URL values', () => {
  const raw = JSON.stringify({ operationName: 'GuidedFactCheckPrepare', query: 'mutation GuidedFactCheckPrepare($documentId: ID!) { secret }', variables: { documentId: 'SECRET_VARIABLE' }, extensions: { token: 'SECRET_EXTENSION' } });
  const result = inspectGraphqlEnvelope(request(raw), options);
  assert.equal(result.status, 'parsed');
  assert.equal(result.operations[0].name, 'GuidedFactCheckPrepare');
  assert.equal(result.operations[0].queryKind, 'mutation');
  assert.equal(result.operations[0].variableCount, 1);
  assert.doesNotMatch(JSON.stringify(result), /SECRET_VARIABLE|SECRET_EXTENSION|SECRET_URL|documentId|\$documentId/);
});

test('batched, unlisted and anonymous operations retain counts and uncertainty', () => {
  const body = JSON.stringify([
    { operationName: 'GuidedFactCheckSubmit', query: '# comment\n query GuidedFactCheckSubmit { viewer }', variables: {} },
    { operationName: 'SECRET_PRIVATE_NAME', query: 'subscription SECRET_PRIVATE_NAME { changes }' },
    { query: '{ viewer }' },
  ]);
  const result = inspectGraphqlEnvelope(request(body), options);
  assert.equal(result.batchCount, 3);
  assert.deepEqual(result.operations.map(x => x.nameStatus), ['allowed', 'unlisted', 'absent']);
  assert.deepEqual(result.operations.map(x => x.queryKind), ['query', 'subscription', 'unknown']);
  assert.doesNotMatch(JSON.stringify(result), /SECRET_PRIVATE_NAME/);
});

test('missing, malformed and oversized bodies remain explicit', () => {
  assert.equal(inspectGraphqlEnvelope(request(undefined), options).status, 'body-unavailable');
  assert.equal(inspectGraphqlEnvelope(request('{SECRET'), options).status, 'invalid-json');
  assert.equal(inspectGraphqlEnvelope(request('x'.repeat(1025)), { ...options, maxPostBytes: 1024 }).status, 'oversized');
});

test('origin, path and method fence prevent unrelated requests', () => {
  const raw = JSON.stringify({ operationName: 'GuidedFactCheckPrepare', variables: { secret: 'SECRET_VARIABLE' } });
  for (const url of ['https://other.example.test/api/graphql', 'https://studio.example.test/api/graphql/other']) {
    const result = inspectGraphqlEnvelope(request(raw, url), options);
    assert.equal(result.status, 'not-target');
    assert.equal(result.operations, undefined);
  }
  const wrongMethod = request(raw);
  wrongMethod.params.request.method = 'GET';
  assert.equal(inspectGraphqlEnvelope(wrongMethod, options).status, 'not-target');
});
