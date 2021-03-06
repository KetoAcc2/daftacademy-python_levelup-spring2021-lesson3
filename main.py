import sqlite3

from fastapi import Cookie, FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from typing import List

from starlette import status
from starlette.responses import JSONResponse

app = FastAPI()


@app.on_event("startup")
async def startup():
    app.db_connection = sqlite3.connect("db/northwind.db")
    app.db_connection.text_factory = lambda b: b.decode(errors="ignore")  # northwind specific


@app.on_event("shutdown")
async def shutdown():
    app.db_connection.close()


class Category(BaseModel):
    name: str


@app.post('/categories', status_code=201)
async def categories_post(category: Category):
    cursor = app.db_connection.execute("INSERT INTO Categories (CategoryName) VALUES (?)", (category.name,))
    app.db_connection.commit()
    new_categories_id = cursor.lastrowid
    app.db_connection.row_factory = sqlite3.Row
    categories = app.db_connection.execute(
        """SELECT CategoryID id, CategoryName name FROM Categories WHERE CategoryID = ?""",
        (new_categories_id,)).fetchone()
    return categories


@app.put('/categories/{id}', status_code=200)
async def categories_id(category: Category, id: int):
    app.db_connection.execute(
        "UPDATE Categories SET CategoryName = ? WHERE CategoryID = ?", (
            category.name, id,)
    )
    app.db_connection.commit()
    app.db_connection.row_factory = sqlite3.Row
    data = app.db_connection.execute(
        """SELECT CategoryID id, CategoryName name FROM Categories WHERE CategoryID = ?""",
        (id,)).fetchone()
    if data is None:
        raise HTTPException(status_code=404)
    return data


@app.delete('/categories/{id}', status_code=200)
async def categories_delete(id: int):
    cursor = app.db_connection.execute(
        "DELETE FROM Categories WHERE CategoryID = ?", (id,)
    )
    app.db_connection.commit()
    if cursor.rowcount:
        return {"deleted": 1}
    raise HTTPException(status_code=404)


# @app.post("/categories", status_code=201)
# async def get_categories(category: Category):
#     connection = app.db_connection
#     execution = connection.execute(
#         "insert into Categories (CategoryName) values (?)",
#         (category.name, )
#     )
#     connection.commit()
# 
#     cursor = app.db_connection.cursor()
#     cursor.row_factory = sqlite3.Row
#     result = cursor.execute(
#         """
#         SELECT CategoryID id, CategoryName name 
#         FROM Categories 
#         WHERE CategoryID = ?
#         """,
#         (execution.lastrowid,)).fetchone()
#     return result
# 
# 
# @app.put("/categories{category_id}", status_code=200)
# async def update_category(category: Category, category_id: int = 0):
#     if category_id == 0:
#         raise HTTPException(status_code=404)
# 
#     connection = app.db_connection
#     connection.execute(
#         "update Categories set CategoryName = ? where CategoryId = ?"
#         , (category.name, category_id, )
#     )
#     connection.commit()
# 
#     cursor = app.db_connection.cursor()
#     cursor.row_factory = sqlite3.Row
#     result = cursor.execute(
#         f"""
#         select CategoryId as id, CategoryName as name
#         from Categories
#         where CategoryId = {category_id}
#         """
#     ).fetchone()
# 
#     if result is None:
#         raise HTTPException(status_code=404)
# 
#     return result


# @app.delete("/categories/{category_id}", status_code=200)
# async def delete_category(category_id: int = 0):
#     if category_id == 0:
#         raise HTTPException(status_code=404)
# 
#     cursor = app.db_connection.cursor()
#     cursor.row_factory = sqlite3.Row
#     count = cursor.execute(
#         f"""
#         select CategoryId
#         from Categories
#         where CategoryId = {category_id}
#         """
#     ).fetchone()
# 
#     if count is None:
#         raise HTTPException(status_code=404)
# 
#     cursor = app.db_connection.execute(
#         "DELETE FROM Categories WHERE CategoryId = ?", (category_id,)
#     )
#     app.db_connection.commit()
#     if not cursor.rowcount:
#         raise HTTPException(status_code=404)
#     return {"deleted": 1}


@app.get("/products/{product_id}/orders", status_code=200)
async def products_orders(product_id: int = 0):
    if product_id == 0:
        raise HTTPException(status_code=404)

    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row

    count = cursor.execute(
        f"""
        select ProductId as id, ProductName as name
        from Products
        where ProductId = {product_id}
        """
    ).fetchone()

    if count is None:
        raise HTTPException(status_code=404)

    result = cursor.execute(
        f"""
        select o.OrderId as id, c.CompanyName as customer, od.Quantity as quantity,
               round((od.UnitPrice * od.Quantity) - (od.Discount * (od.UnitPrice * od.Quantity)), 2) as total_price
        from Orders o inner join Customers c on o.CustomerId = c.CustomerId
                      inner join 'Order Details' od on o.OrderId = od.OrderId
        where od.ProductId = {product_id}
        order by o.OrderId
        """
    ).fetchall()

    if result is None:
        raise HTTPException(status_code=404)

    return dict(orders=result)


@app.get("/products_extended", status_code=200)
async def products_extended():
    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute(
        f"""
        select p.ProductId as id, p.ProductName as name, 
               ct.CategoryName as category, s.CompanyName as supplier 
        from Products p inner join Categories ct on p.CategoryId = ct.CategoryId
                        inner join Suppliers s on p.SupplierId = s.SupplierId
        order by p.ProductId 
        """
    ).fetchall()

    if result is None:
        return JSONResponse(status_code=404)

    return dict(products_extended=result)


@app.get("/employees", status_code=200)
async def get_employees(limit: int = 1, offset: int = 0, order: str = 'EmployeeID'):
    valid_orders = ("FirstName", "LastName", "City")
    if order != "EmployeeID":
        if order == 'first_name':
            order = valid_orders[0]
        elif order == 'last_name':
            order = valid_orders[1]
        elif order == 'city':
            order = valid_orders[2]
        else:
            return JSONResponse(status_code=400)

    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute(
        f"""select EmployeeID id, LastName last_name, FirstName first_name, City city 
        from Employees 
        order by {order} 
        LIMIT {limit} OFFSET {offset};"""
    ).fetchall()

    return dict(employees=result)


@app.get("/products/{id}", status_code=200)
async def products_id(id: int):
    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute(
        "select ProductId as id, ProductName as name "
        "from Products "
        "where ProductId = ?", (id,)
    ).fetchone()

    if result is None:
        return JSONResponse(status_code=404)

    return result


@app.get("/customers", status_code=200)
async def customers():
    # app.db_connection.row_factory = lambda cursor, x: x[0]
    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute(
        "SELECT CustomerId as id, CompanyName as name,"
        "COALESCE(Address, '') || ' ' || COALESCE(PostalCode, '')"
        " || ' ' ||  COALESCE(City, '') || ' ' || COALESCE(Country, '')"
        " as full_address "
        "FROM Customers "
        "order by upper(CustomerId);"
    ).fetchall()

    return dict(customers=result)


@app.get("/categories", status_code=200)
async def get_categories():
    cursor = app.db_connection.cursor()
    cursor.row_factory = sqlite3.Row
    result = cursor.execute("select categoryid as id, categoryname as name "
                            "from categories "
                            "order by categoryid;").fetchall()
    return dict(categories=result)


if __name__ == '__main__':
    uvicorn.run(app)
