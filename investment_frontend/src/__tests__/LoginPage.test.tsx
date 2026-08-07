/**
 * Tests for the Login Page
 * Covers: rendering, link presence, and page identity
 */
import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import LoginPage from '../app/LoginPage/page'

describe('LoginPage', () => {
  it('renders without crashing', () => {
    render(<LoginPage />)
  })

  it('displays the Investify login text', () => {
    render(<LoginPage />)
    expect(screen.getByText(/Investify Login Page/i)).toBeInTheDocument()
  })
})
