import test from 'node:test';
import assert from 'node:assert/strict';
import { inspectProtocolEnvelope, summarizeProtocolEnvelopes } from './protocol-envelope.mjs';

const frame = (payloadData, opcode = 1, method = 'Network.webSocketFrameReceived') => ({ method, sequence: 7,
  params: { timestamp: 12.5, response: { opcode, payloadData } } });
const options = { allowedEvents: ['chat_stream_delta', 'safe_event'], allowedTopicFamilies: ['room'] };

test('Phoenix array and object envelopes retain only allowlisted structural fields', () => {
  for (const raw of [
    JSON.stringify(['join-secret', 'ref-secret', 'room:private-person@example.com', 'chat_stream_delta', { token: 'sk-sensitive', text: 'SECRET_PAYLOAD' }]),
    JSON.stringify({ join_ref: 'secret', ref: 'secret', topic: 'room:private-person@example.com', event: 'chat_stream_delta', payload: { text: 'SECRET_PAYLOAD' } }),
  ]) {
    const result = inspectProtocolEnvelope(frame(raw), options);
    assert.equal(result.protocol, 'phoenix');
    assert.equal(result.eventName, 'chat_stream_delta');
    assert.equal(result.topicFamily, 'room');
    assert.equal(result.payloadBytes, Buffer.byteLength(raw));
    assert.doesNotMatch(JSON.stringify(result), /SECRET_PAYLOAD|private-person|join-secret|ref-secret|sk-sensitive/);
  }
});

test('unknown Phoenix event and topic names do not enter output', () => {
  const result = inspectProtocolEnvelope(frame(JSON.stringify([null, null, 'secret-topic:123', 'privateEmailJane', { accessToken: 'SECRET_PAYLOAD' }])), options);
  assert.equal(result.status, 'unlisted-event');
  assert.equal(result.eventName, undefined);
  assert.equal(result.topicFamily, undefined);
  assert.doesNotMatch(JSON.stringify(result), /privateEmailJane|secret-topic|SECRET_PAYLOAD/);
});

test('GraphQL WebSocket and Socket.IO event envelopes strip IDs and payloads', () => {
  const gql = inspectProtocolEnvelope(frame(JSON.stringify({ id: 'private-id', type: 'next', payload: { data: 'SECRET_PAYLOAD' } })), options);
  assert.equal(gql.protocol, 'graphql-ws');
  assert.equal(gql.eventName, 'next');
  const socket = inspectProtocolEnvelope(frame('42' + JSON.stringify(['safe_event', { secret: 'SECRET_PAYLOAD' }]), 1, 'Network.webSocketFrameSent'), options);
  assert.equal(socket.protocol, 'socket.io');
  assert.equal(socket.direction, 'sent');
  assert.equal(socket.eventName, 'safe_event');
  assert.doesNotMatch(JSON.stringify([gql, socket]), /private-id|SECRET_PAYLOAD/);
});

test('binary, malformed, oversized and unsupported frames stay unnamed', () => {
  const cases = [frame('U0VDUkVU', 2), frame('{"payload":"SECRET_PAYLOAD"'), frame('x'.repeat(1025)), frame('SECRET_PAYLOAD', 8)];
  const statuses = ['binary', 'malformed', 'oversized', 'unsupported-opcode'];
  for (let i = 0; i < cases.length; i++) {
    const result = inspectProtocolEnvelope(cases[i], { ...options, maxPayloadBytes: 1024 });
    assert.equal(result.status, statuses[i]);
    assert.equal(result.eventName, undefined);
    assert.doesNotMatch(JSON.stringify(result), /SECRET_PAYLOAD/);
  }
});

test('aggregate cadence totals sanitized records without raw frames', () => {
  const a = inspectProtocolEnvelope(frame(JSON.stringify([null, null, 'room:1', 'chat_stream_delta', { text: 'a' }])), options);
  const b = inspectProtocolEnvelope({ ...frame(JSON.stringify([null, null, 'room:2', 'chat_stream_delta', { text: 'b' }])), params: { timestamp: 13.25, response: { opcode: 1, payloadData: JSON.stringify([null, null, 'room:2', 'chat_stream_delta', { text: 'b' }]) } } }, options);
  const [summary] = summarizeProtocolEnvelopes([a, b]);
  assert.equal(summary.count, 2);
  assert.equal(summary.firstTimestamp, 12.5);
  assert.equal(summary.lastTimestamp, 13.25);
  assert.equal(summary.bytes, a.payloadBytes + b.payloadBytes);
});
