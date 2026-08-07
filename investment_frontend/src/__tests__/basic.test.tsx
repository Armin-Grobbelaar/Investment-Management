import '@testing-library/jest-dom'
import { render, screen } from '@testing-library/react'
import React from 'react'

// Simple test component
const TestComponent = () => <div>Hello Investment App</div>

describe('Basic Frontend Test', () => {
  it('renders a greeting', () => {
    render(<TestComponent />)
    const element = screen.getByText('Hello Investment App')
    expect(element).toBeInTheDocument()
  })
})
