from app.service import products


def test_create_product(product_vegetable, category_food, unit_kg):
    assert product_vegetable.id is not None
    assert product_vegetable.name == 'Огурцы'
    assert product_vegetable.category_id == category_food.id
    assert product_vegetable.unit_id == unit_kg.id


def test_create_product_no_category(product_no_category, unit_l):
    assert product_no_category.id is not None
    assert product_no_category.name == 'Вода минеральная'
    assert product_no_category.category_id is None
    assert product_no_category.unit_id == unit_l.id


def test_create_few_products(few_products):
    assert len(few_products) == 3
    names = [p.name for p in few_products]
    assert 'Помидоры' in names
    assert 'Морковь' in names
    assert 'Капуста' in names


def test_update_product(product_vegetable, category_food, unit_kg):
    updated_product = products.update_product(
        product_vegetable.id,
        name='Огурцы свежие',
        category_id=category_food.id,
        unit_id=unit_kg.id,
    )
    assert updated_product.id == product_vegetable.id
    assert updated_product.name == 'Огурцы свежие'
    assert updated_product.category_id == category_food.id
    assert updated_product.unit_id == unit_kg.id


def test_get_product_by_id(product_vegetable):
    product = products.get_product(product_vegetable.id)
    assert product is not None
    assert product.id == product_vegetable.id
    assert product.name == 'Огурцы'
    assert product.category_id == product_vegetable.category_id
    assert product.unit_id == product_vegetable.unit_id


def test_get_list_product(few_products):
    product_list = products.list_products()
    assert len(product_list) == 3
    product_names = [product.name for product in product_list]
    assert 'Помидоры' in product_names
    assert 'Морковь' in product_names
    assert 'Капуста' in product_names
