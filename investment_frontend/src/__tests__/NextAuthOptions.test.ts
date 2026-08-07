/**
 * Tests for the NextAuth options configuration
 * Covers: provider configuration, credentials authorize logic
 */
import { options } from '../app/api/auth/[...nextauth]/options'

// Mock next-auth providers so we don't need real OAuth credentials
jest.mock('next-auth/providers/github', () => jest.fn((config) => ({ id: 'github', ...config })))
jest.mock('next-auth/providers/credentials', () => jest.fn((config) => ({ id: 'credentials', ...config })))

describe('NextAuth options', () => {
  it('has exactly two providers configured', () => {
    expect(options.providers).toHaveLength(2)
  })

  it('first provider is GitHub', () => {
    const github = options.providers[0] as any
    expect(github.id).toBe('github')
  })

  it('second provider is Credentials', () => {
    const creds = options.providers[1] as any
    expect(creds.id).toBe('credentials')
  })

  describe('CredentialsProvider authorize', () => {
    let authorize: Function

    beforeEach(() => {
      const creds = options.providers[1] as any
      authorize = creds.authorize
    })

    it('returns the user when username and password match', async () => {
      const result = await authorize({ username: 'Dave', password: 'nextauth' })
      expect(result).not.toBeNull()
      expect(result?.id).toBe('42')
      expect(result?.name).toBe('Dave')
    })

    it('returns null for wrong password', async () => {
      const result = await authorize({ username: 'Dave', password: 'wrongpassword' })
      expect(result).toBeNull()
    })

    it('returns null for wrong username', async () => {
      const result = await authorize({ username: 'NotDave', password: 'nextauth' })
      expect(result).toBeNull()
    })

    it('returns null for empty credentials', async () => {
      const result = await authorize({ username: '', password: '' })
      expect(result).toBeNull()
    })

    it('returns null for missing credentials', async () => {
      const result = await authorize(undefined)
      expect(result).toBeNull()
    })
  })
})
