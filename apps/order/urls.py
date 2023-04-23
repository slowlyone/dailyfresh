
from django.conf.urls import  url
from  order.view import  OrderPlaceView,OrderCommitView
urlpatterns = [
    url(r'^place$',OrderPlaceView.as_view(),name='place'),  #提交订单页面显示
    url(r'^commits$',OrderCommitView.as_view(),name='commit'),  #订单创建
    url(r'^comment/(?P<order_id>.+)$',OrderCommitView.as_view(),name='comment'),  #订单评论
]

