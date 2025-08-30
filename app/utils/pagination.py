# app/utils/pagination.py

def paginate(items, page=1, per_page=10):
    """
    Paginer une liste d'items.
    
    :param items: liste ou iterable d'éléments
    :param page: page actuelle (1-indexée)
    :param per_page: nombre d'éléments par page
    :return: tuple (items_page, page, total_pages)
    """
    total_items = len(items)
    total_pages = (total_items + per_page - 1) // per_page
    page = max(1, min(page, total_pages))  # sécurise la page
    start = (page - 1) * per_page
    end = start + per_page
    items_page = items[start:end]
    return items_page, page, total_pages
