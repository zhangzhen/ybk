from datetime import datetime

from .mangaa import (
    Model,
    IntField,
    FloatField,
    StringField,
    DateTimeField,
)

from .quote import Quote
from .models import Collection


class Transaction(Model):

    """ 用户交易信息 """
    meta = {
        'indexes': [
            [[('user', 1), ('type_', 1),
              ('exchange', 1), ('symbol', 1)], {}],
            [[('user', 1), ('operated_at', 1)], {}],
        ],
    }
    exchange = StringField(blank=False)         # 交易所ID(简称)
    symbol = StringField(blank=False)           # 交易代码

    user = StringField(blank=False)
    type_ = StringField(blank=False)            # buy/sell
    price = FloatField(blank=False)
    quantity = IntField(blank=False)
    operated_at = DateTimeField(auto='created')

    @classmethod
    def user_total_transactions(cls, user):
        """ 用户总操作次数 """
        return cls.find({'user': user}).count()

    @classmethod
    def user_recent_transactions(cls, user, offset=0, limit=None):
        """ 用户最近的操作 """
        qs = cls.find({'user': user}, sort=[('operated_at', -1)])
        if offset:
            qs.skip(offset)
        if limit:
            qs.limit(limit)
        return list(qs)


class Position(Model):

    """ 用户持仓信息 """

    meta = {
        'unique': ['user', 'exchange', 'symbol'],
        'indexes': [
            [[('user', 1), ('exchange', 1), ('symbol', 1)], {}],
        ],
    }

    exchange = StringField(blank=False)         # 交易所ID(简称)
    symbol = StringField(blank=False)           # 交易代码

    user = StringField(blank=False)
    quantity = FloatField(blank=False, default=0)

    @classmethod
    def num_exchanges(cls, user):
        """ 用户持有多少个交易所的持仓 """
        return len(set(p.exchange for p in
                       cls.find({'user': user}, {'exchange': 1})))

    @classmethod
    def num_collections(cls, user):
        """ 用户持有多少不同的藏品 """
        return len(list(cls.find({'user': user}, {'_id': 1})))

    @classmethod
    def num_sold(cls, user):
        """ 用户已卖出过多少个藏品 """
        return len(set('{exchange}_{symbol}'.format(**t._data) for t in
                       Transaction.find({'user': user, 'type_': 'sell'},
                                        {'exchange': 1, 'symbol': 1})))

    @classmethod
    def user_position(cls, user):
        """ 目前持仓概况 """
        collections = {}
        for p in cls.find({'user': user}):
            pair = (p.exchange, p.symbol)
            collections.setdefault(pair, 0)
            collections[pair] += p.quantity
        buy_info = {}
        for t in Transaction.find({'user': user, 'type_': 'buy'},
                                  sort=[('operated_at', 1)]):
            pair = (t.exchange, t.symbol)
            if pair in collections:
                buy_info.setdefault(pair, [0, 0, None])
                buy_info[pair][0] += t.quantity
                buy_info[pair][1] += t.quantity * t.price
                if not buy_info[pair][2]:
                    buy_info[pair][2] = t.operated_at
        sell_info = {}
        for t in Transaction.find({'user': user, 'type_': 'sell'},
                                  sort=[('operated_at', -1)]):
            pair = (t.exchange, t.symbol)
            if pair in collections:
                sell_info.setdefault(pair, [0, 0, None])
                sell_info[pair][0] += t.quantity
                sell_info[pair][1] += t.quantity * t.price
                if not sell_info[pair][2]:
                    sell_info[pair][2] = t.operated_at
        position = []
        for pair, quantity_amount in buy_info.items():
            exchange, symbol = pair
            quantity, amount, first_buy_at = quantity_amount
            if quantity:
                avg_buy_price = amount / quantity
                realized_profit = 0
                last_sell_at = datetime.utcnow()
                if pair in sell_info:
                    quantity2, amount2, last_sell_at = sell_info[pair]
                    quantity -= quantity2
                    realized_profit = amount2 - avg_buy_price * quantity2

                assert quantity == collections[pair], '交易和库存对不上'
                latest_price = Quote.latest_price(exchange, symbol)
                increase = Quote.increase(exchange, symbol)
                if not latest_price:
                    latest_price = avg_buy_price
                unrealized_profit = (latest_price - avg_buy_price) * quantity
                past_days = max(1, (last_sell_at - first_buy_at).days)
                annual_profit = (365 / past_days) * \
                    (unrealized_profit + realized_profit)
                if quantity > 0:
                    position.append({
                        'exchange': exchange,
                        'symbol': symbol,
                        'name': Collection.get_name(exchange, symbol),
                        'avg_buy_price': avg_buy_price,
                        'quantity': quantity,
                        'latest_price': latest_price,
                        'increase': increase,
                        'total_increase': latest_price / avg_buy_price - 1,
                        'realized_profit': realized_profit,
                        'unrealized_profit': unrealized_profit,
                        'annual_profit': annual_profit,
                    })
        return sorted(position, key=lambda x: x['exchange'])

    @classmethod
    def average_increase(cls, user):
        """ 平均涨幅 """
        position = cls.user_position(user)
        if len(position):
            return sum(p['total_increase'] for p in position) / len(position)

    @classmethod
    def unrealized_profit(cls, user):
        """ 未实现收益(浮盈) """
        return sum(p['unrealized_profit'] for p in
                   cls.user_position(user))

    @classmethod
    def realized_profit(cls, user):
        """ 已实现收益 """
        return sum(p['realized_profit'] for p in
                   cls.user_position(user))

    @classmethod
    def annual_profit(cls, user):
        """ 年化收益 """
        return sum(p['annual_profit'] for p in
                   cls.user_position(user))

    @classmethod
    def do_op(cls, t, reverse=False):
        c = cls.find_one({'user': t.user,
                          'exchange': t.exchange,
                          'symbol': t.symbol})
        if not c:
            if reverse:
                return False
            elif t.type_ == 'buy':
                c = cls({'user': t.user,
                         'exchange': t.exchange,
                         'symbol': t.symbol,
                         'quantity': t.quantity})
            else:
                return False
        elif t.type_ == 'buy':
            c.quantity += t.quantity
        elif t.type_ == 'sell':
            c.quantity -= t.quantity

        if c.quantity >= 0:
            c.save()
            return True
        else:
            return False