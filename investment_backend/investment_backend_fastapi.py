
from investment_database_functions import *
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Response, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
#import io

investment_api = FastAPI()

class AddUserRequest(BaseModel):
    username: str
    user_surname: str


class AddInvestmentRequest(BaseModel):
    database_name: str
    institution_name: str
    initial_investment_date: str
    investment_type: str
    investment_name: str
    investment_ticker: str
    unit_currency: str
    initial_unit_price: float
    unit_price: float
    number_of_units_held: float
    total_dividends_received: float
    total_tax_paid: float
    total_fees_paid: float
    investment_fee: float
    investment_status: str

origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:3003",
    "http://127.0.0.1:3003",
    "http://192.168.10.100:3003"
]

investment_api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@investment_api.get("/investment_summary/{database_name}")
def fastapi_get_investment_summary(database_name):
    global investment_summary
    investment_summary = get_investment_summary(database_name)

    return Response(investment_summary.to_json(orient="records"), media_type="application/json")

@investment_api.post("/add_user")
def fastapi_add_user(user_data: AddUserRequest):
    # Call your add_user function with the data from the request
    add_user(user_data.username, user_data.user_surname)
    return {"message": "User successfully added"}

@investment_api.get("/all_investment_values/{database_name}")
def fastapi_get_all_investment_values(database_name: str):
    investment_values = get_all_investment_values(database_name)
    return Response(investment_values.to_json(orient="records"), media_type="application/json")

@investment_api.get("/investment_data/{database_name}/{investment_name}/{column_name}")
async def fastapi_get_investment_values(database_name: str, investment_name: str, column_name: str):
    global investment_values
    investment_values = pd.DataFrame()
    if (investment_values.empty):
        investment_values = get_all_investment_values(database_name)
    investment_values_filttered = investment_values[investment_values["investment_name"] == investment_name][column_name]
    return Response(investment_values_filttered.to_json(orient="records"), media_type="application/json")

@investment_api.post("/add_investment/{database_name}")
async def fastapi_add_investment(database_name: str, investment_data: AddInvestmentRequest):
    create_connection(database_name)
    add_investment(
        database_name = investment_data.database_name,
        institution_name=investment_data.institution_name,
        initial_investment_date=investment_data.initial_investment_date,
        investment_type=investment_data.investment_type,
        investment_name=investment_data.investment_name,
        investment_ticker=investment_data.investment_ticker,
        unit_currency=investment_data.unit_currency,
        initial_unit_price=investment_data.initial_unit_price,
        unit_price=investment_data.unit_price,
        number_of_units_held=investment_data.number_of_units_held,
        total_dividends_received=investment_data.total_dividends_received,
        total_tax_paid=investment_data.total_tax_paid,
        total_fees_paid=investment_data.total_fees_paid,
        investment_fee=investment_data.investment_fee,
        investment_status=investment_data.investment_status,
    )
    return {"message": "Investment added successfully"}

@investment_api.post("/import_unit_prices/")
async def import_unit_prices(
    file: UploadFile = File(...),
    investment_name: str = Form(...)
):
    try:
        # Save the uploaded file content temporarily in memory
        file_content = await file.read()
        file_name = "temp_unit_prices.csv"
        
        # Write the file content to a temporary file
        with open(file_name, "wb") as temp_file:
            temp_file.write(file_content)
        
        # Call the existing function
        import_unit_prices_csv(file_name, investment_name, "USD")

        return {"message": "Unit prices imported successfully", "investment_name": investment_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
