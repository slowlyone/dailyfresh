from django.contrib import admin
from  goods.models import GoodsType,IndexGoodsBanner,IndexPromotionBanner,IndexTypeGoodsBanner
from  django.core.cache import  cache
# Register your models here.

class BaseModelAdmin(admin.ModelAdmin):

    def  save_model(self, request, obj, form, change):
        #新增 或更新表中的数据时候 调用
        super().save_model(request,obj,form,change)

        #发出任务，让celery worker重新生成首页静态页 。【异步发出，】
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('index_page_data')  #清楚首页的缓存数据

    def delete_model(self,request,obj):
        #删除表中的数据时调用
        super().delete_model(request,obj)

        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

        cache.delete('index_page_data')  #清楚首页的缓存数据。后台管理员一旦修改数据，就清除首页--已经查询的缓存。

class IndexPromotionBannerAdmin(BaseModelAdmin):   #因为有很多模型类；使用继承思想，防止重复代码
    pass

class IndexTypeGoodsBannerAdmin(BaseModelAdmin):
    pass

class IndexGoodsBannerAdmin(BaseModelAdmin):
    pass

class  GoodsTypeAdmin(BaseModelAdmin):
    pass



admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)     #IndexPromotionBanner类定义它对应的一个管理类、通过它里面的属性，
 # 控制前端显示的内容。
admin.site.register(GoodsType,GoodsTypeAdmin)
admin.site.register(IndexTypeGoodsBanner,IndexTypeGoodsBannerAdmin)
admin.site.register(IndexGoodsBanner,IndexGoodsBannerAdmin)