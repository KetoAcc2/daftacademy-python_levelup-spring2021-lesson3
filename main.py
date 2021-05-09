import sqlite3

from fastapi import Cookie, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from typing import List

app = FastAPI()


@app.on_event("startup")
async def startup():
    app.db_connection = sqlite3.connect("db/northwind.db")
    app.db_connection.text_factory = lambda b: b.decode(errors="ignore")  # northwind specific


@app.on_event("shutdown")
async def shutdown():
    app.db_connection.close()


@app.get("/customers", status_code=200)
async def customers():
    # app.db_connection.row_factory = lambda cursor, x: x[0]
    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute("SELECT CustomerId, CompanyName , IFNULL(Address, '') || ' ' || IFNULL(PostalCode, '') "
                            "|| ' ' ||  IFNULL(City, '') || ' ' || IFNULL(Country, '') as full_address "
                            "FROM Customers "
                            "order by CustomerId").fetchall()
    return {
        "customers": [
            {"id": f'{x["CustomerId"]}', "name": f'{x["CompanyName"]}', "full_address": f'{x["full_address"]}'}
            for x in result
        ]
    }


@app.get("/categories", status_code=200)
async def get_categories():
    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute("select categoryid, categoryname "
                            "from categories "
                            "order by categoryid").fetchall()
    return {
        "categories": [
            {"id": f'{x["categoryid"]}', "name": f'{x["categoryname"]}'}
            for x in result
        ]
    }


if __name__ == '__main__':
    uvicorn.run(app)
