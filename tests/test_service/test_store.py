from app.service import stores


def test_create_store(single_store):
    assert single_store.id is not None
    assert single_store.name == 'Магнит'
    assert single_store.description == 'Магнит - магазин для всей семьи'


def test_few_stores(few_stores):
    assert len(few_stores) == 3
    assert few_stores[0].name == 'Пятерочка'
    assert few_stores[1].description is None
    assert few_stores[2].name == 'Дикси'


def test_get_store_by_id(single_store):
    store = stores.get_store(single_store.id)
    assert store is not None
    assert store.id == single_store.id
    assert store.name == 'Магнит'
    assert store.description == 'Магнит - магазин для всей семьи'


def test_get_list_store(few_stores):
    store_list = stores.list_stores()
    assert len(store_list) >= 3
    store_names = [store.name for store in store_list]
    assert 'Пятерочка' in store_names
    assert 'Яндекс.Лавка' in store_names
    assert 'Дикси' in store_names


def test_update_store(single_store):
    updated_store = stores.update_store(
        single_store.id,
        name='Магнит Экспресс',
        description='Магнит Экспресс - магазин для занятых людей'
    )
    assert updated_store.id == single_store.id
    assert updated_store.name == 'Магнит Экспресс'
    assert updated_store.description == (
        'Магнит Экспресс - магазин для занятых людей'
    )
