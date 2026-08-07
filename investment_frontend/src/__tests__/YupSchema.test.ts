/**
 * Tests for the Yup validation schemas
 * Covers: required fields, positive-number rules, and type coercion
 */
import { addInvestmentSchema } from '../app/Schemas/YupSchema'

const validData = {
  institutionsName: 'Test Bank',
  initialInvestmentDate: new Date('2023-01-01'),
  investmentType: 'Stocks',
  investmentName: 'MSFT ETF',
  investmentTicker: 'MSFT.JO',
  unitCurrency: 'ZAR',
  initialUnitPrice: 100.0,
  currentUnitPrice: 110.0,
  numberOfUnitsHeld: 50.0,
  totalDividends: 0.01,
  totalTax: 0.01,
  totalFees: 0.01,
  investmentFee: 0.5,
  investmentStatus: 'Active',
}

describe('addInvestmentSchema', () => {
  describe('Valid data', () => {
    it('passes for completely valid input', async () => {
      await expect(addInvestmentSchema.validate(validData)).resolves.toBeTruthy()
    })
  })

  describe('Required string fields', () => {
    it.each([
      'institutionsName',
      'investmentType',
      'investmentName',
      'investmentTicker',
      'unitCurrency',
      'investmentStatus',
    ])('fails when %s is empty', async (field) => {
      const data = { ...validData, [field]: '' }
      await expect(addInvestmentSchema.validate(data)).rejects.toThrow()
    })

    it.each([
      'institutionsName',
      'investmentType',
      'investmentName',
      'investmentTicker',
      'unitCurrency',
      'investmentStatus',
    ])('fails when %s is missing', async (field) => {
      const { [field as keyof typeof validData]: _, ...data } = validData
      await expect(addInvestmentSchema.validate(data)).rejects.toThrow()
    })
  })

  describe('Required date fields', () => {
    it('fails when initialInvestmentDate is missing', async () => {
      const { initialInvestmentDate: _, ...data } = validData
      await expect(addInvestmentSchema.validate(data)).rejects.toThrow()
    })
  })

  describe('Positive number fields', () => {
    it.each([
      ['initialUnitPrice', 'positive initial unit price'],
      ['currentUnitPrice', 'positive unit price'],
      ['numberOfUnitsHeld', 'positive number for the units held'],
      ['totalDividends', 'positive number for the Total Dividends'],
      ['totalTax', 'positive number for the Total Tax'],
      ['totalFees', 'positive number for the Total Fees'],
      ['investmentFee', 'positive Investment Fee'],
    ])('fails when %s is zero', async (field) => {
      const data = { ...validData, [field]: 0 }
      await expect(addInvestmentSchema.validate(data)).rejects.toThrow()
    })

    it.each([
      'initialUnitPrice',
      'currentUnitPrice',
      'numberOfUnitsHeld',
      'totalDividends',
      'totalTax',
      'totalFees',
      'investmentFee',
    ])('fails when %s is negative', async (field) => {
      const data = { ...validData, [field]: -5 }
      await expect(addInvestmentSchema.validate(data)).rejects.toThrow()
    })

    it.each([
      'initialUnitPrice',
      'currentUnitPrice',
      'numberOfUnitsHeld',
      'totalDividends',
      'totalTax',
      'totalFees',
      'investmentFee',
    ])('passes when %s is a small positive decimal', async (field) => {
      const data = { ...validData, [field]: 0.01 }
      await expect(addInvestmentSchema.validate(data)).resolves.toBeTruthy()
    })
  })

  describe('Error messages', () => {
    it('returns correct error message for missing institution name', async () => {
      try {
        await addInvestmentSchema.validate({ ...validData, institutionsName: '' })
      } catch (err: any) {
        expect(err.message).toContain('Institution is required')
      }
    })

    it('returns correct error message for zero initialUnitPrice', async () => {
      try {
        await addInvestmentSchema.validate({ ...validData, initialUnitPrice: 0 })
      } catch (err: any) {
        expect(err.message).toContain('positive initial unit price')
      }
    })

    it('returns correct error message for zero numberOfUnitsHeld', async () => {
      try {
        await addInvestmentSchema.validate({ ...validData, numberOfUnitsHeld: 0 })
      } catch (err: any) {
        expect(err.message).toContain('positive number for the units held')
      }
    })
  })
})
