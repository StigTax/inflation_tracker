from app.service import categories


def test_create_categoty(category_food):
    assert category_food.id is not None
    assert category_food.name == 'Овощи'
    assert category_food.description == 'Свежие овощи'


def test_create_few_categories(few_categories):
    assert len(few_categories) == 3
    assert few_categories[0].name == 'Напитки'
    assert few_categories[1].name == 'Молочные продукты'
    assert few_categories[2].name == 'Хлебобулочные изделия'


def test_update_category(category_food):
    updated_category = categories.update_category(
        category_food.id,
        name='Фрукты',
        description='Свежие фрукты',
    )
    assert updated_category.id == category_food.id
    assert updated_category.name == 'Фрукты'
    assert updated_category.description == 'Свежие фрукты'


def test_get_category_by_id(category_food):
    fetched_category = categories.get_category(
        category_food.id,
    )
    assert fetched_category is not None
    assert fetched_category.id == category_food.id
    assert fetched_category.name == category_food.name
    assert fetched_category.description == category_food.description


def test_get_list_category(few_categories):
    category_list = categories.list_categories()
    assert len(category_list) == len(few_categories)
    category_ids = [category.id for category in category_list]
    for cat in few_categories:
        assert cat.id in category_ids
