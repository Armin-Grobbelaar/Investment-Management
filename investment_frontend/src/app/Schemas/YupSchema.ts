import * as yup from "yup";

export const addInvestmentSchema = yup.object().shape({
    institutionsName: yup.string().required("A Institution is required"),
    initialInvestmentDate: yup.date().required("A Initial Investment Date is required"),
    investmentType: yup.string().required("A Investment Type is required"),
    investmentName: yup.string().required("A Name for the Investment is required"),
    investmentTicker: yup.string().required("A Investment Ticker or class is required"),
    unitCurrency: yup.string().required("Unit Currency for the Investment is required"),
    initialUnitPrice: yup.number().positive("Please provide a positive initial unit price").required("A Initial Unit Price is required"),
    currentUnitPrice: yup.number().positive("Please provide a positive unit price").required("A Unit Price is required"),
    numberOfUnitsHeld: yup.number().positive("Please provide a positive number for the units held").required("Number of Units Held is required"),
    totalDividends: yup.number().positive("Please provide a positive number for the Total Dividends").required("Dividends are required"),
    totalTax: yup.number().positive("Please provide a positive number for the Total Tax").required("Tax is required"),
    totalFees: yup.number().positive("Please provide a positive number for the Total Fees").required("Fees are required"),
    investmentFee: yup.number().positive("Please provide a positive Investment Fee").required("A Investment Fee is required"),
    investmentStatus: yup.string().required("Investment Status for the Investment is required"),
})
