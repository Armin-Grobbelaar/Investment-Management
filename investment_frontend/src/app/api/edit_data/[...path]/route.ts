import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:3337';

async function handler(req: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const pathStr = path.join('/');
  const url = new URL(req.url);
  const queryString = url.search;
  const backendUrl = `${BACKEND_URL}/edit_data/${pathStr}${queryString}`;

  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

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

    return new NextResponse(responseText, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
      },
    });
  } catch (error: any) {
    return NextResponse.json(
      { detail: `Backend error: ${error.message}` },
      { status: 502 }
    );
  }
}

export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
export const PATCH = handler;
