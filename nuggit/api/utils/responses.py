# api/utils/responses.py
def success_response(data, message="Success"):
    return {"message": message, "data": data}
