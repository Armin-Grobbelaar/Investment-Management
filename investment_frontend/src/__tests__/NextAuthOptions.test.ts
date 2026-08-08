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

    const OLD_USERNAME = process.env.ADMIN_USERNAME
    const OLD_PASSWORD = process.env.ADMIN_PASSWORD

    beforeEach(() => {
      const creds = options.providers[1] as any
      authorize = creds.authorize
    })

    afterAll(() => {
      // Restore env so we don't leak test credentials into other tests
      if (OLD_USERNAME === undefined) delete process.env.ADMIN_USERNAME
      else process.env.ADMIN_USERNAME = OLD_USERNAME
      if (OLD_PASSWORD === undefined) delete process.env.ADMIN_PASSWORD
      else process.env.ADMIN_PASSWORD = OLD_PASSWORD
    })

    it('returns the user when username and password match', async () => {
      process.env.ADMIN_USERNAME = 'Dave'
      process.env.ADMIN_PASSWORD = 'nextauth'
      const result = await authorize({ username: 'Dave', password: 'nextauth' })
      expect(result).not.toBeNull()
      expect(result?.id).toBe('1')
      expect(result?.name).toBe('Dave')
    })

    it('returns null for wrong password', async () => {
      process.env.ADMIN_USERNAME = 'Dave'
      process.env.ADMIN_PASSWORD = 'nextauth'
      const result = await authorize({ username: 'Dave', password: 'wrongpassword' })
      expect(result).toBeNull()
    })

    it('returns null for wrong username', async () => {
      process.env.ADMIN_USERNAME = 'Dave'
      process.env.ADMIN_PASSWORD = 'nextauth'
      const result = await authorize({ username: 'NotDave', password: 'nextauth' })
      expect(result).toBeNull()
    })

    it('returns null when credentials env vars are unset', async () => {
      delete process.env.ADMIN_USERNAME
      delete process.env.ADMIN_PASSWORD
      const result = await authorize({ username: 'Dave', password: 'nextauth' })
      expect(result).toBeNull()
    })

    it('returns null for empty credentials', async () => {
      process.env.ADMIN_USERNAME = 'Dave'
      process.env.ADMIN_PASSWORD = 'nextauth'
      const result = await authorize({ username: '', password: '' })
      expect(result).toBeNull()
    })

    it('returns null for missing credentials', async () => {
      const result = await authorize(undefined)
      expect(result).toBeNull()
    })
  })
})
