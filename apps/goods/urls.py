from django.conf.urls import  url
from goods.views import  IndexView,DetailView,ListView,OrderPayView,CheckPayView,CommentView

urlpatterns = [
    url(r'^index$',IndexView.as_view(), name = 'index'),  #首页
    url(r'^goods/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'), # 详情页
    url(r'^list/(?P<type_id>\d+)/(?P<page>\d+)$', ListView.as_view(), name='list'), # 列表页
    url(r'^pay$',OrderPayView.as_view(),name='pay'),  #订单支付
    url(r'^check$',CheckPayView.as_view(),name='check'), #查询支付交易结构
]

