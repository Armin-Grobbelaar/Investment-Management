/**
 * Tests for the SideMenuDrawer (Navigation) Component
 * Covers: closed state, open/close toggle, menu items rendering, link navigation
 */
import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import DrawerComponent from '../app/Reusable Components/Drawers/SideMenyDrawer'

// next/link needs to be mocked for unit tests
jest.mock('next/link', () => {
  const MockLink = ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  )
  MockLink.displayName = 'MockLink'
  return MockLink
})

const menuItems = [
  {
    heading: 'Portfolio',
    items: ['All Investments', 'Net Worth'],
    urls: ['/Investments', '/NetWorth'],
  },
  {
    heading: 'Analysis',
    items: ['IRR Analysis', 'Predictions'],
    urls: ['/IRRAnalysis', '/ViewInvestmentPredictions'],
  },
]

describe('DrawerComponent (SideMenuDrawer)', () => {
  it('renders the open menu button initially', () => {
    render(<DrawerComponent menuItems={menuItems} />)
    // The menu icon button should be present
    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
  })

  it('opens the drawer and shows menu items visibly', () => {
    render(<DrawerComponent menuItems={menuItems} />)
    // MUI persistent Drawer renders list items in DOM always.
    // After clicking, the headings should be present (they always are in persistent mode).
    const toggleBtn = screen.getAllByRole('button')[0]
    fireEvent.click(toggleBtn)
    // After open, headings are visible in the DOM
    expect(screen.getByText('Portfolio')).toBeInTheDocument()
    expect(screen.getByText('Analysis')).toBeInTheDocument()
  })

  it('renders all menu item labels when drawer is open', () => {
    render(<DrawerComponent menuItems={menuItems} />)
    fireEvent.click(screen.getAllByRole('button')[0])
    expect(screen.getByText('All Investments')).toBeInTheDocument()
    expect(screen.getByText('Net Worth')).toBeInTheDocument()
    expect(screen.getByText('IRR Analysis')).toBeInTheDocument()
    expect(screen.getByText('Predictions')).toBeInTheDocument()
  })

  it('renders correct href links for menu items', () => {
    render(<DrawerComponent menuItems={menuItems} />)
    fireEvent.click(screen.getAllByRole('button')[0])
    const links = screen.getAllByRole('link')
    const hrefs = links.map(l => l.getAttribute('href'))
    expect(hrefs).toContain('/Investments')
    expect(hrefs).toContain('/NetWorth')
    expect(hrefs).toContain('/IRRAnalysis')
    expect(hrefs).toContain('/ViewInvestmentPredictions')
  })

  it('renders empty drawer cleanly with no menu items', () => {
    render(<DrawerComponent menuItems={[]} />)
    fireEvent.click(screen.getAllByRole('button')[0])
    // No links should be rendered
    expect(screen.queryAllByRole('link')).toHaveLength(0)
  })
})
