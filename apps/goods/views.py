from django.shortcuts import render,redirect
from  django.views.generic import  View
from  goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner,GoodsSKU
from order.models import  OrderGoods
from  django.core.cache import  cache
from  django_redis import  get_redis_connection
from django.core.paginator import Paginator
# Create your views here.

class IndexView(View):

    def get(self,request):
        ''' 首页'''
            #尝试从缓存中获取数据
        context= cache.get('index_page_data')

        if context is None:
            print('验证缓存：第一次查数据库')
             # 获取 商品的种类信息      【商品种类信息 在GoodsType里面】
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息  【轮播表  IndexGoodsBanner ，它的index字段 是顺序】
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息  【促销活动 表】
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            # type_goods_banners = IndexTypeGoodsBanner.objects.all()  XX
                #因为 在模板里面难以分类，不能全部查all()完，需要获取每一个种类的 它的这个信息
            for type in types:  #遍历每一种类型， 得到Goodtype类型的对象、就可以得到对应商品的展示信息。
                #获取type种类首页分类商品的图片展示信息
                image_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=1).order_by('index')
                #获取type种类首页分类商品的文字展示信息
                title_banners=IndexTypeGoodsBanner.objects.filter(type=type,display_type=0).order_by('index')

                #动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
                type.image_banners = image_banners
                type.title_banners = title_banners          #也对应是 IndexTypeGoodsBanner


            context= {
                'types':types,
                'goods_banners':goods_banners,
                'promotion_banners':promotion_banners}
                # 'cart_count':cart_count

            cache.set('index_page_data',context,3600)   #设置缓存


        #获取用户购物中商品的数目
        cart_count = 0
        user = request.user
        if user.is_authenticated():  #用户已经登陆
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)

        #组织模板上下文
        context.update(cart_count=cart_count)
        #使用模板
        return  render(request,'index.html',context)


class DetailView(View):
    #详情页
    def get(self,request,goods_id):
        #显示详情页
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reversed('goods:index'))

        #获取商品的分类信息
        types= GoodsType.objects.all()

        #获取商品的评论信息
        sku_orders = OrderGoods.objects.filter(sku=sku).exclude(comment="")   #排除空的评论， 得到有1评论的内容

        #获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]

        #获取同一个SPU的其它规格商品。一个SPU包含多个SKU
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.gooods).exclude(id=goods_id)

        #获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated():  #用户已经登陆
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            cart_count= conn.hlen(cart_key)

            #添加用户的历史纪录
            conn = get_redis_connection('default')
            history_key = 'history_%d'%user.id
            #移除列表中的goods_id
            conn.lrem(history_key,0,goods_id)
            #把goods_id 插入到列表的左侧
            conn.lpush(history_key,goods_id)
            #只保存用户最近浏览的5条信息
            conn.ltrim(history_key,0,4)


        #组织模板上下文
        context = {
            'sku':sku,'types':types,
            'sku_orders':sku_orders,
            'new_skus': new_skus,
            'same_spu_skus':same_spu_skus,
            'cart_count':cart_count
        }

        #使用模板
        return render(request,'detail.html',context)
#/list/种类id/页码/排序方式
#第二种:  /list/种类id/页码?sort=排序方式
#第三种 /list?type_id=种类id&page=页码&sort=排序方式
class  ListView(View):

    def get(self,request,type_id,page):
        #显示列表页
        try:
            type= GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return  redirect(reversed('goods:index'))

        #获取商品的分类信息
        types = GoodsType.objects.all()

        #获取排序的方式
             # sort=default 按照默认id排序
            # sort=price 按照商品价格排序
             # sort=hot 按照商品销量排序

        sort = request.GET.get('sort')

        if sort == 'price':

            skus = GoodsSKU.objects.filter(type=type).order_by('price')

        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')

        else:
            sort='default'
            skus = GoodsSKU.objects.filter(type=type).order_by('-id')

        #对数据进行分页  。表示每一页1条数据
        paginator=Paginator(skus,1)
        #获取第page页的内容
        try:
            page= int(page)
        except:
            page=1

        if page > paginator.num_pages: #大于总页数
            page=1

        #获取第page页的Page实例对象
        skus_page = paginator.page(page)

        #tod:进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页

        num_pages= paginator.num_pages
        if num_pages <5:
            pages = range(1,num_pages+1)
        elif page <=3:
            pages = range(1,6)

        elif num_pages - page <=2:
            pages = range(num_pages-4,num_pages+1)

        else:
            pages = range(page-2,page+3)

        #获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]


        #获取用户购物车中的商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            conn = get_redis_connection('default')
            cart_key  = 'cart_%d'%user.id
            cart_count = conn.hlen(cart_key)
        #组织模板上下文
        context = {
            'type':type,'types':types,
            'skus_page':skus_page,
            'new_skus':new_skus,
            'cart_count':cart_count,
            'pages':pages,
            'sort':sort
        }
        #使用模板
        return render(request,'list.html',context)
































