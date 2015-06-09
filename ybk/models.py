#!/usr/bin/env python
# -*- coding: utf-8 -*-
import math
from datetime import datetime, timedelta

import requests

import ybk.config
from ybk.mangaa import (
    Model,
    IntField,
    FloatField,
    StringField,
    BooleanField,
    DateTimeField,
)


class WechatAccessToken(Model):

    """ 微信ACCESS_TOKEN """

    meta = {
        'idformat': 'access_token',
        'indexes': [
            [[('expires_at', 1)], {'expireAfterSeconds': 0}],
        ],
    }
    access_token = StringField()
    expires_in = IntField()
    expires_at = DateTimeField()
    updated_at = DateTimeField(auto='modified')

    @classmethod
    def get_access_token(cls):
        instance = cls.find_one()
        if instance:
            return instance['access_token']
        else:
            appid = ybk.config.conf.get('wechat_appid')
            appsecret = ybk.config.conf.get('wechat_appsecret')
            grant_type = 'client_credential'
            url = 'https://api.weixin.qq.com/cgi-bin/token'
            params = {
                'grant_type': grant_type,
                'appid': appid,
                'secret': appsecret,
            }
            j = requests.get(url, params=params, timeout=(3, 7)).json()
            expires_at = datetime.utcnow() + timedelta(seconds=j['expires_in'])
            cls({'access_token': j['access_token'],
                 'expires_in': j['expires_in'],
                 'expires_at': expires_at}).save()
            return j['access_token']


class WechatEvent(Model):

    """ 微信事件

    暂时只保存, 不处理
    """
    xml = StringField()  # xml格式数据主题
    updated_at = DateTimeField(auto='modified')


class Exchange(Model):

    """ 交易所 """
    meta = {
        'idformat': '{abbr}',
        'unique': ['abbr'],
    }

    name = StringField()
    abbr = StringField()  # 简称
    url = StringField()
    updated_at = DateTimeField(auto='modified')


class Announcement(Model):

    """ 公告信息 """
    meta = {
        'idformat': '{url}',
        'unique': ['url'],
        'indexes': [
            [[('published_at', 1), ('type_', 1)], {}],
            [[('exchange', 1), ('type_', 1)], {}],
        ],
    }
    exchange = StringField()        # 交易所简称(ID)
    type_ = StringField()           # 申购("offer")/中签("result")
    url = StringField()             # 公告链接
    title = StringField()           # 公告标题
    html = StringField()            # 原始html
    published_at = DateTimeField()  # 交易所发布时间
    updated_at = DateTimeField(auto='modified')

    parsed = BooleanField(default=False)


class Stamp(Model):

    """ Stamp/Coin/Card 交易品"""

    meta = {
        'idformat': '{exchange}_{symbol}',
        'unique': ['exchange', 'symbol'],
    }

    exchange = StringField(blank=False)        # 交易所ID(简称)
    symbol = StringField(blank=False)          # 交易代码
    name = StringField(blank=False)            # 交易名
    type_ = StringField(default="邮票", blank=False)           # "邮票"/"钱币"/"卡片"
    status = StringField(default="申购中", blank=False)          # "申购中"/"已上市"

    issuer = StringField()          # 发行机构
    texture = StringField()         # 材质
    price_forsale = FloatField()    # 挂牌参考价
    quantity_all = IntField()       # 挂牌总数量
    quantity_forsale = IntField()   # 限售总数

    offer_fee = FloatField(default=0, blank=False)        # 申购手续费
    offer_quantity = IntField(blank=False)     # 供申购数量 *
    offer_price = FloatField(blank=False)      # 申购价格 *
    offer_accmax = IntField(blank=False)       # 单账户最大中签数 *
    offer_overbuy = BooleanField(blank=False)  # 是否可超额申购 *
    offer_cash_ratio = FloatField(blank=False)  # 资金配售比例 *

    change_min = FloatField()       # 最小价格变动单位
    change_limit_1 = FloatField()   # 首日涨跌幅
    change_limit = FloatField()     # 正常日涨跌幅
    pickup_min = IntField()         # 最小提货量
    trade_limit = FloatField()      # 单笔最大下单量

    offers_at = DateTimeField(blank=False)     # 申购日 *
    draws_at = DateTimeField(blank=False)      # 抽签日 *
    trades_at = DateTimeField(blank=False)     # 上市交易日 *

    invest_mv = FloatField()       # 申购市值(Market Value)
    invest_cash = FloatField()     # 申购资金 *

    updated_at = DateTimeField(auto='modified')

    @property
    def offer_mv(self):
        """ 申购总市值(Market Value) """
        return self.offer_quantity * self.offer_price

    @property
    def offer_max_invest(self):
        """ 最大申购资金 """
        if self.offer_overbuy:
            return float('inf')
        else:
            return self.offer_mv + \
                self.offer_fee * self.offer_accmax

    @property
    def result_ratio_cash(self):
        """ 资金中签率 """
        if self.status == "已上市" and self.invest_cash:
            return self.offer_mv * self.offer_cash_ratio / self.invest_cash

    @property
    def result_ratio_mv(self):
        """ 市值中签率 """
        if self.status == "已上市" and self.invest_mv:
            return self.offer_mv * (1 - self.offer_cash_ratio) \
                / self.invest_mv

    @property
    def offer_min_invest(self):
        """ 必中最低申购资金 """
        if self.status == "已上市" and self.invest_cash:
            magnitude = math.ceil(math.log10(1 / self.result_ratio_cash))
            return self.offer_price * 10 ** magnitude * (1 + self.offer_fee)


class Quote(object):

    """ 交易行情信息 """

    meta = {
        'idformat': '{exchange}_{symbol}',
        'unique': ['exchange', 'symbol'],
        'indexes': [
            [[('exchange', 1), ('symbol', 1),
              ('quote_type', 1), ('quote_at', 1)], {}],
        ],
    }

    exchange = StringField(blank=False)         # 交易所ID(简称)
    symbol = StringField(blank=False)           # 交易代码

    quote_type = StringField(blank=False)       # 1m/5m/15m/30m/1h/4h/1d/1w/1m
    quote_at = DateTimeField(blank=False)       # 交易时间

    open_ = FloatField(blank=False)             # 周期开盘价
    high = FloatField(blank=False)              # 周期最高价
    low = FloatField(blank=False)               # 周期最低价
    close = FloatField(blank=False)             # 周期收盘价
    volume = IntField(blank=False)              # 周期成交量
    amount = FloatField(blank=False)            # 周期成交额
