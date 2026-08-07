/**
 * Tests for frontend API proxy calls
 * These test the fetch() calls made by the frontend to the Next.js API routes,
 * which in turn proxy to the FastAPI backend.
 */

// Mock the global fetch
global.fetch = jest.fn()

const mockFetch = global.fetch as jest.Mock

describe('Frontend API: add_investment', () => {
  const validPayload = {
    institution_name: 'Test Bank',
    initial_investment_date: '2023-01-01',
    investment_type: 'Stocks',
    investment_name: 'MSFT ETF',
    investment_ticker: 'MSFT.JO',
    unit_currency: 'ZAR',
    initial_unit_price: 100.0,
    unit_price: 110.0,
    number_of_units_held: 50.0,
    total_dividends_received: 0.01,
    total_tax_paid: 0.01,
    total_fees_paid: 0.01,
    investment_fee: 0.5,
    investment_status: 'Active',
  }

  beforeEach(() => mockFetch.mockClear())

  it('calls the correct endpoint with POST method', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ message: 'Investment added', investment_id: 1 }),
    })

    const response = await fetch('/api/add_investment/Investments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(validPayload),
    })

    expect(mockFetch).toHaveBeenCalledWith('/api/add_investment/Investments', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    }))
    expect(response.ok).toBe(true)
    const data = await response.json()
    expect(data.investment_id).toBe(1)
  })

  it('returns error response on API failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({ message: 'Duplicate investment name' }),
    })

    const response = await fetch('/api/add_investment/Investments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(validPayload),
    })

    expect(response.ok).toBe(false)
    const data = await response.json()
    expect(data.message).toBe('Duplicate investment name')
  })

  it('sends the body payload as JSON', async () => {
    mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({}) })

    await fetch('/api/add_investment/Investments', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(validPayload),
    })

    const [, callOptions] = mockFetch.mock.calls[0]
    const body = JSON.parse(callOptions.body)
    expect(body.institution_name).toBe('Test Bank')
    expect(body.investment_ticker).toBe('MSFT.JO')
    expect(body.unit_price).toBe(110.0)
  })
})

describe('Frontend API: dashboard data', () => {
  beforeEach(() => mockFetch.mockClear())

  it('fetches dashboard data from correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        totalValue: 150000,
        totalInvestments: 5,
        currency: 'ZAR',
      }),
    })

    const response = await fetch('/api/dashboard/Investments')
    expect(mockFetch).toHaveBeenCalledWith('/api/dashboard/Investments')
    const data = await response.json()
    expect(data.totalValue).toBe(150000)
    expect(data.totalInvestments).toBe(5)
  })

  it('handles network errors gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    await expect(
      fetch('/api/dashboard/Investments')
    ).rejects.toThrow('Network error')
  })
})

describe('Frontend API: investment list', () => {
  beforeEach(() => mockFetch.mockClear())

  it('fetches investment summary from correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        investments: [
          { id: 1, investment_name: 'MSFT ETF', unit_price: 110.0 },
          { id: 2, investment_name: 'SP500 ETF', unit_price: 220.0 },
        ],
      }),
    })

    const response = await fetch('/api/investments/summary/Investments')
    const data = await response.json()
    expect(data.investments).toHaveLength(2)
    expect(data.investments[0].investment_name).toBe('MSFT ETF')
  })
})
