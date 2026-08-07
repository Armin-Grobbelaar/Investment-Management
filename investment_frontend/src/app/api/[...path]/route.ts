import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:3337';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path);
}

async function proxyRequest(req: NextRequest, path: string[]) {
  const pathStr = path.join('/');
  const url = new URL(req.url);
  const queryString = url.search;
  const backendUrl = `${BACKEND_URL}/${pathStr}${queryString}`;

  try {
    const headers: Record<string, string> = {};

    // Copy content-type from original request
    const originalContentType = req.headers.get('content-type');
    if (originalContentType) {
      headers['Content-Type'] = originalContentType;
    }

    let body: string | undefined = undefined;
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      body = await req.text();
    }

    const response = await fetch(backendUrl, {
      method: req.method,
      headers,
      body,
    });

    const responseText = await response.text();

    // Try to parse as JSON for forwarding
    let responseBody: any = responseText;
    try {
      responseBody = JSON.parse(responseText);
    } catch {
      // Not JSON - pass through as text
    }

    return NextResponse.json(responseBody, {
      status: response.status,
    });
  } catch (error: any) {
    return NextResponse.json(
      { detail: `Backend error: ${error.message}` },
      { status: 502 }
    );
  }
}