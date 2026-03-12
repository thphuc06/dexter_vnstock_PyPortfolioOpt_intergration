#!/usr/bin/env bun
import 'dotenv/config';
import { runAgentForMessage } from './gateway/agent-runner.js';
import { DEFAULT_MODEL, DEFAULT_PROVIDER } from './model/llm.js';
import { getSetting } from './utils/config.js';
import { getDefaultModelForProvider } from './utils/model.js';

const PORT = parseInt(process.env.DEXTER_SERVER_PORT || '3000', 10);

const savedProvider = getSetting('provider', DEFAULT_PROVIDER);
const savedModelId = getSetting('modelId', null) as string | null;
const savedModel = savedModelId ?? getDefaultModelForProvider(savedProvider) ?? DEFAULT_MODEL;

interface AskRequest {
  question: string;
  model?: string;
  modelProvider?: string;
}

interface SuccessResponse {
  answer: string;
  success: true;
}

interface ErrorResponse {
  error: string;
  success: false;
}

interface HealthResponse {
  status: string;
  timestamp: string;
}

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      ...CORS_HEADERS,
    },
  });
}

async function handleAsk(request: Request): Promise<Response> {
  try {
    const body = (await request.json()) as AskRequest;
    if (!body.question || typeof body.question !== 'string' || body.question.trim() === '') {
      return jsonResponse(
        { error: 'Question is required and must be a non-empty string', success: false } as ErrorResponse,
        400
      );
    }

    const question = body.question.trim();
    const modelProvider = body.modelProvider ?? savedProvider;
    const model = body.model ?? savedModel;
    const sessionKey = crypto.randomUUID();

    const answer = await runAgentForMessage({
      sessionKey,
      query: question,
      model,
      modelProvider,
      maxIterations: 10,
    });

    return jsonResponse({ answer, success: true } as SuccessResponse);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    return jsonResponse(
      { error: `Failed to process question: ${errorMessage}`, success: false } as ErrorResponse,
      500
    );
  }
}

function handleHealth(): Response {
  return jsonResponse({
    status: 'ok',
    timestamp: new Date().toISOString(),
  } as HealthResponse);
}

function handleOptions(): Response {
  return new Response(null, {
    status: 204,
    headers: CORS_HEADERS,
  });
}

function handleNotFound(): Response {
  return jsonResponse(
    { error: 'Not found', success: false } as ErrorResponse,
    404
  );
}

export function createHttpHandler() {
  return async function handleHttpRequest(request: Request): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    if (method === 'OPTIONS') {
      return handleOptions();
    }

    if (method === 'POST' && path === '/ask') {
      return handleAsk(request);
    }

    if (method === 'GET' && path === '/health') {
      return handleHealth();
    }

    return handleNotFound();
  };
}

export function startServer() {
  const server = Bun.serve({
    port: PORT,
    fetch: createHttpHandler(),
    error(error) {
      console.error('Server error:', error);
      return jsonResponse(
        { error: 'Internal server error', success: false } as ErrorResponse,
        500
      );
    },
  });

  console.log(`Dexter HTTP API server listening on http://localhost:${PORT}`);
  console.log(`  POST http://localhost:${PORT}/ask - Submit questions to the agent`);
  console.log(`  GET  http://localhost:${PORT}/health - Health check`);
  return server;
}

if (import.meta.main) {
  startServer();
}

