import type { NextAuthOptions } from 'next-auth'
import GitHubProvider from 'next-auth/providers/github'
import CredentialsProvider from 'next-auth/providers/credentials'

const sessionSecret = process.env.NEXTAUTH_SECRET || '';
if (!sessionSecret) {
    console.warn(
        '[nextauth] NEXTAUTH_SECRET is not set. Sessions will be unsigned and invalidated on ' +
        'every server restart. Set NEXTAUTH_SECRET in your environment (e.g. `openssl rand -base64 32`).'
    );
}

export const options: NextAuthOptions = {
    secret: sessionSecret,
    callbacks: {
        async jwt({ token, user }) {
            if (user) {
                token.user_id = (user as any).id;
                token.database_name = (user as any).database_name;
                token.access_token = (user as any).token;
            }
            return token;
        },
        async session({ session, token }) {
            (session as any).user_id = token.user_id;
            (session as any).database_name = token.database_name;
            (session as any).access_token = token.access_token;
            return session;
        }
    },
    providers: [
        GitHubProvider({
            clientId: process.env.GITHUB_ID as string,
            clientSecret: process.env.GITHUB_SECRET as string,
        }),
        CredentialsProvider({
            name: "Credentials",
            credentials: {
                username: {
                    label: "Username:",
                    type: "text",
                    placeholder: "your-cool-username"
                },
                password: {
                    label: "Password:",
                    type: "password",
                    placeholder: "your-awesome-password"
                }
            },
            async authorize(credentials) {
                if (!credentials?.username || !credentials?.password) {
                    return null;
                }

                try {
                    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:3337';
                    const response = await fetch(`${backendUrl}/verify_user`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            username: credentials.username,
                            password: credentials.password
                        })
                    });

                    if (!response.ok) {
                        return null;
                    }

                    const user = await response.json();
                    return {
                        id: user.id.toString(),
                        name: user.username,
                        email: user.email,
                        database_name: user.database_name || "investments_app",
                        token: user.token
                    };
                } catch (error) {
                    console.error('Authentication error:', error);
                    return null;
                }
            }
        })
    ],
}