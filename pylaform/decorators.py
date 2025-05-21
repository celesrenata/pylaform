def catch_error(func):
    """Decorator to catch and handle errors gracefully."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Handle the error appropriately
            # For example, log it and return a friendly error message
            print(f"Error in {func.__name__}: {str(e)}")
            return {"error": str(e)}, 500
    return wrapper