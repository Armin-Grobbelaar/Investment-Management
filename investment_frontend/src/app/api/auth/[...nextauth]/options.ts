import type { NextAuthOptions } from 'next-auth'
import GitHubProvider from 'next-auth/providers/github'
import CredentialsProvider from 'next-auth/providers/credentials'

// Session signing secret must come from the environment — never hardcode it.
const sessionSecret = process.env.NEXTAUTH_SECRET || '';
if (!sessionSecret) {
    console.warn(
        '[nextauth] NEXTAUTH_SECRET is not set. Sessions will be unsigned and invalidated on ' +
        'every server restart. Set NEXTAUTH_SECRET in your environment (e.g. `openssl rand -base64 32`).'
    );
}

export const options: NextAuthOptions = {
    secret: sessionSecret,
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
                // This is where you need to retrieve user data 
                // to verify with credentials
                // Docs: https://next-auth.js.org/configuration/providers/credentials
                //
                // SECURITY: Never hardcode usernames/passwords in source.
                // Credentials must come from environment variables.
                // TODO: Replace this env-var comparison with a backend user
                // lookup (e.g. the /add_user endpoint or the users table) that
                // verifies against a stored password hash.
                const username = process.env.ADMIN_USERNAME;
                const password = process.env.ADMIN_PASSWORD;

                if (!username || !password) {
                    console.warn(
                        '[nextauth] ADMIN_USERNAME / ADMIN_PASSWORD are not set. ' +
                        'Credentials sign-in is disabled until they are configured.'
                    );
                    return null;
                }

                if (credentials?.username === username && credentials?.password === password) {
                    return { id: "1", name: username }
                } else {
                    return null
                }
            }
        })
    ],
} 