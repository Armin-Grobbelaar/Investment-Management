/**
 * Tests for Reusable DialogComponent
 * Covers: rendering, props, button interactions, and close behaviour
 */
import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import DialogComponent from '../app/Reusable Components/Dialog Pop Up/dialogpopup'

const defaultProps = {
  open: true,
  onClose: jest.fn(),
  mainHeading: 'Confirm Investment',
  headings: ['Institution', 'Investment Name', 'Unit Price'],
  values: ['Test Bank', 'MSFT ETF', 120.5],
  buttons: [
    { label: 'Cancel', onClick: jest.fn(), variant: 'text' as const, color: 'secondary' as const },
    { label: 'Confirm', onClick: jest.fn(), variant: 'contained' as const, color: 'primary' as const },
  ],
}

describe('DialogComponent', () => {
  beforeEach(() => jest.clearAllMocks())

  it('renders the main heading', () => {
    render(<DialogComponent {...defaultProps} />)
    expect(screen.getByText('Confirm Investment')).toBeInTheDocument()
  })

  it('renders all field headings', () => {
    render(<DialogComponent {...defaultProps} />)
    expect(screen.getByText('Institution')).toBeInTheDocument()
    expect(screen.getByText('Investment Name')).toBeInTheDocument()
    expect(screen.getByText('Unit Price')).toBeInTheDocument()
  })

  it('renders all field values', () => {
    render(<DialogComponent {...defaultProps} />)
    expect(screen.getByText('Test Bank')).toBeInTheDocument()
    expect(screen.getByText('MSFT ETF')).toBeInTheDocument()
    expect(screen.getByText('120.5')).toBeInTheDocument()
  })

  it('renders all action buttons', () => {
    render(<DialogComponent {...defaultProps} />)
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirm' })).toBeInTheDocument()
  })

  it('calls the correct button handler when Confirm is clicked', () => {
    render(<DialogComponent {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }))
    expect(defaultProps.buttons[1].onClick).toHaveBeenCalledTimes(1)
    expect(defaultProps.buttons[0].onClick).not.toHaveBeenCalled()
  })

  it('calls the correct button handler when Cancel is clicked', () => {
    render(<DialogComponent {...defaultProps} />)
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    expect(defaultProps.buttons[0].onClick).toHaveBeenCalledTimes(1)
  })

  it('does not show content when open is false', () => {
    render(<DialogComponent {...defaultProps} open={false} />)
    // MUI renders Dialog to DOM but hides it — the dialog role should not be visible
    const dialog = screen.queryByRole('dialog')
    expect(dialog).toBeNull()
  })

  it('handles undefined values gracefully', () => {
    const propsWithUndefined = {
      ...defaultProps,
      headings: ['Missing Field'],
      values: [undefined],
    }
    render(<DialogComponent {...propsWithUndefined} />)
    expect(screen.getByText('Missing Field')).toBeInTheDocument()
  })

  it('handles empty headings and values arrays', () => {
    const emptyProps = { ...defaultProps, headings: [], values: [] }
    render(<DialogComponent {...emptyProps} />)
    expect(screen.getByText('Confirm Investment')).toBeInTheDocument()
  })
})
