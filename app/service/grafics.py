"""Скрипт построения графиков аналитики."""

import matplotlib.pyplot as plt
import pandas as pd

from app.service.analytics import product_inflation_index

res = product_inflation_index(
    product_id=1,
    group_by='month',
    price_mode='paid'
)
ts = pd.DataFrame(res['points'])
ts['period'] = pd.to_datetime(ts['period'])

fig, ax = plt.subplots()
ax.plot(ts['period'], ts['index_100'])
ax.set_title('Индекс инфляции')
ax.set_xlabel('Период')
ax.set_ylabel('Индекс')
ax.grid(True)
plt.show()
