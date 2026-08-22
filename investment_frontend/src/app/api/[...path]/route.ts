import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { options } from '../auth/[...nextauth]/options';

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
  
  // Public paths bypass authentication checks
  const isPublicPath = 
    pathStr === 'verify_user' || 
    pathStr === 'add_user' || 
    pathStr === 'health' || 
    pathStr === 'currencies' || 
    pathStr === 'api/currencies';

  const headers: Record<string, string> = {};

  if (!isPublicPath) {
    const session = await getServerSession(options);
    const accessToken = (session as any)?.access_token;

    if (!session) {
      return NextResponse.json(
        { detail: 'Unauthorized: No active session found' },
        { status: 401 }
      );
    }

    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }
  }

  const url = new URL(req.url);
  const backendUrl = `${BACKEND_URL}/${pathStr}${url.search}`;

  try {
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

    const contentType = response.headers.get('content-type') || '';

    // Binary responses (PDFs, images, etc.) — stream through directly
    if (
      contentType.includes('application/pdf') ||
      contentType.includes('application/octet-stream') ||
      contentType.includes('image/')
    ) {
      const buffer = await response.arrayBuffer();
      const responseHeaders: Record<string, string> = {
        'Content-Type': contentType,
        'Content-Length': buffer.byteLength.toString(),
      };
      const disposition = response.headers.get('content-disposition');
      if (disposition) {
        responseHeaders['Content-Disposition'] = disposition;
      }
      return new Response(buffer, {
        status: response.status,
        headers: responseHeaders,
      });
    }

    // JSON / text responses
    const responseText = await response.text();
    let responseBody: any = responseText;
    try {
      responseBody = JSON.parse(responseText);
    } catch {
      return new Response(responseText, {
        status: response.status,
        headers: { 'Content-Type': contentType || 'text/plain' },
      });
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