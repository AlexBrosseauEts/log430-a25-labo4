"""
Orders (read-only model)
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import json
import time
from db import get_redis_conn, get_sqlalchemy_session
from collections import defaultdict
from logger import Logger
from orders.models.order import Order
from orders.models.order_item import OrderItem
from sqlalchemy.sql import func

logger = Logger.get_instance("order_reports")

def get_order_by_id(order_id):
    """Get order by ID from Redis"""
    r = get_redis_conn()
    raw_order = r.hgetall(f"order:{order_id}")
    order = {}
    for key, value in raw_order.items():
        found_key = key.decode('utf-8') if isinstance(key, bytes) else key
        found_value = value.decode('utf-8') if isinstance(value, bytes) else value
        order[found_key] = found_value
    return order

def get_highest_spending_users_mysql():
    """Get report of highest spending users from MySQL"""
    session = get_sqlalchemy_session()
    limit = 10
    
    try:
        results = session.query(
            Order.user_id,
            func.sum(Order.total_amount).label('total_expense')
        ).group_by(Order.user_id)\
         .order_by(func.sum(Order.total_amount).desc())\
         .limit(limit)\
         .all()
        
        return [
            {
                "user_id": result.user_id,
                "total_expense": round(float(result.total_expense), 2)
            }
            for result in results
        ]
    finally:
        session.close()

def get_best_selling_products_mysql():
    """Get report of best selling products by quantity sold from MySQL"""
    session = get_sqlalchemy_session()
    limit = 100
    result = []
    
    try:
        order_items = session.query(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label('total_sold')
        ).group_by(OrderItem.product_id)\
         .order_by(func.sum(OrderItem.quantity).desc())\
         .limit(limit)\
         .all()
        
        for order_item in order_items:
            result.append({
                "product_id": order_item[0],
                "quantity": round(order_item[1], 2)
            })

        return result

    finally:
        session.close()

def get_highest_spending_users_redis():
    """Get report of highest spending users from Redis"""
    r = get_redis_conn()
    # Labo: lire depuis le cache avant de calculer
    report_in_cache = r.hgetall("reports:highest_spending_users")
    if report_in_cache:
        return json.loads(report_in_cache)
    else:
        result = []
        try: 
            start_time = time.time()
            limit = 10
            order_keys = r.keys("order:*")
            spending = defaultdict(float)
            
            for key in order_keys:
                order_data = r.hgetall(key)
                if "user_id" in order_data and "total_amount" in order_data:
                    try:
                        user_id = int(order_data["user_id"])
                        total = float(order_data["total_amount"])
                        spending[user_id] += total
                    except Exception:
                        continue

            # Trier (décroissant), limite X
            highest_spending_users = sorted(spending.items(), key=lambda x: x[1], reverse=True)[:limit]
            for user_id, total in highest_spending_users:
                result.append({
                    "user_id": user_id,
                    "total_expense": round(total, 2)
                })

        except Exception as e:
            return {"error": str(e)}
        finally:
            end_time = time.time()
            logger.debug(f"Executed in {end_time - start_time} seconds")

        r.hset("reports:highest_spending_users", mapping=result)
        r.expire("reports:highest_spending_users", 60)
        return result

def get_best_selling_products_redis():
    """Get report of best selling products by quantity sold from Redis"""
    r = get_redis_conn()
    report_in_cache = r.hgetall("reports:best_selling_products")
    if report_in_cache:
        return json.loads(report_in_cache)
    else:
        result = []
        try:
            start_time = time.time()
            limit = 10
            order_keys = r.keys("order:*")
            product_sales = defaultdict(int)
            
            for order_key in order_keys:
                order_data = r.hgetall(order_key)
                if "items" not in order_data:
                    continue
                try:
                    items = json.loads(order_data["items"])
                except Exception:
                    continue

                for item in items:
                    try:
                        product_id = int(item.get("product_id", 0))
                        quantity = int(item.get("quantity", 0))
                    except Exception:
                        continue
                    if product_id > 0 and quantity > 0:
                        product_sales[product_id] += quantity

            # Trier (décroissant), limite X
            best_selling = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)[:limit]
            for product_id, qty in best_selling:
                result.append({
                    "product_id": product_id,
                    "quantity_sold": qty
                })

        except Exception as e:
            return {"error": str(e)}
        finally:
            end_time = time.time()
            logger.debug(f"Executed in {end_time - start_time} seconds")

        r.hset("reports:best_selling_products", mapping={result})
        r.expire("reports:best_selling_products", 60)
        return result

def get_highest_spending_users():
    """Get report of highest spending users"""
    return get_highest_spending_users_redis()

def get_best_selling_products():
    """Get report of best selling products"""
    return get_best_selling_products_redis()