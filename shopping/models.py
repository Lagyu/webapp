from django.db import models

from django.contrib.auth.models import AbstractBaseUser, AbstractUser, PermissionsMixin, UserManager, User
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail

from django.core.validators import MinValueValidator

import datetime

import uuid as uuid_lib


def get_next():
    try:
        return ShoppingUser.objects.latest('pk').id + 1
    except:
        return 1


# Create your models here.
class ShoppingUser(AbstractBaseUser, PermissionsMixin):
    """ユーザー AbstractUserをコピペし編集"""
    id = models.IntegerField(default=get_next())
    uuid = models.UUIDField(default=uuid_lib.uuid4,
                            primary_key=True, editable=False)
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        help_text=_(
            'Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'),
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    full_name = models.CharField(_('氏名'), max_length=150, blank=True)
    email = models.EmailField(_('email address'), blank=True)

    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_(
            'Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = UserManager()

    EMAIL_FIELD = 'email'
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', ]

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def clean(self):
        super().clean()
        self.email = self.__class__.objects.normalize_email(self.email)

    def email_user(self, subject, message, from_email=None, **kwargs):
        """Send an email to this user."""
        send_mail(subject, message, from_email, [self.email], **kwargs)

    # 既存メソッドの変更
    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name


class Prefecture(models.Model):
    name = models.CharField(max_length=4)
    name_kana = models.CharField(max_length=10)
    is_shown = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ZipCode(models.Model):
    prefecture = models.ForeignKey(Prefecture, on_delete=models.PROTECT)
    code = models.CharField(max_length=7)
    zip_address = models.CharField(max_length=50)

    def __str__(self):
        return self.code

    def get_first_part(self):
        return self.code[0:3]

    def get_last_part(self):
        return self.code[3:]


class Address(models.Model):
    parent_user = models.ForeignKey(ShoppingUser, on_delete=models.PROTECT)
    zipcode = models.ForeignKey(ZipCode, on_delete=models.PROTECT)
    line_1 = models.CharField(max_length=50)
    line_2 = models.CharField(max_length=50)
    building_name = models.CharField(max_length=30)
    is_shown = models.BooleanField(default=True)


class Category(models.Model):
    name = models.CharField(max_length=20, unique=True)
    parent_category = models.ForeignKey("self", on_delete=models.PROTECT, null=True, blank=True)
    is_shown = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Manufacturer(models.Model):
    name = models.CharField(max_length=100)
    is_shown = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, null=False)
    is_shown = models.BooleanField(default=True)
    manufacturer = models.ForeignKey(Manufacturer, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        return self.name


class SubProduct(models.Model):
    parent_product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.IntegerField(validators=[MinValueValidator(1)])
    name = models.CharField(max_length=100)
    is_shown = models.BooleanField(default=True)
    description = models.TextField()

    def __str__(self):
        return self.parent_product.name + "->" + self.name

    def get_short_name(self):
        return self.name

    def get_full_name(self):
        return self.__str__()

    def get_allocatable_stock_num(self):
        return sum([stock_obj.allocatable_num for stock_obj in self.stock_set.all()])


class Warehouse(models.Model):
    name = models.CharField(max_length=30)
    address = models.ForeignKey(Address, on_delete=models.PROTECT)
    is_shown = models.BooleanField(default=True)

    def calc_estimated_time_available(self, to_zip_code: ZipCode) -> datetime.datetime:
        """
        calculates ETA with the address of warehouse and the to_zip_code given.
        :param to_zip_code:
        :return:
        """
        if to_zip_code == self.address:
            return datetime.datetime.now() + datetime.timedelta(days=1)
        else:
            return datetime.datetime.now() + datetime.timedelta(days=2)


class Stock(models.Model):
    product = models.ForeignKey(SubProduct, on_delete=models.CASCADE)
    allocatable_num = models.IntegerField()
    allocated_num = models.IntegerField()
    is_shown = models.BooleanField(default=True)
    warehouse = models.ForeignKey()

    def __str__(self):
        return self.product.name + " / 購入可: "+ str(self.allocatable_num) + "個" +\
               " / 引当済: " + str(self.allocated_num) + "個"


class Cart(models.Model):
    parent_user = models.OneToOneField(ShoppingUser, on_delete=models.CASCADE)


class ProductCart(models.Model):
    parent_cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    sub_product = models.ForeignKey(SubProduct, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    is_shown = models.BooleanField(default=True)

    def get_sum(self):
        return self.sub_product.price * self.quantity

    def get_available_stocks(self):
        stocks = Stock.objects.filter(product=self, allocatable_num__gt=0)
        return stocks


class PaymentMethod(models.Model):
    name = models.CharField(max_length=20)


class Order(models.Model):
    parent_user = models.ForeignKey(ShoppingUser, on_delete=models.PROTECT)
    order_date = models.DateTimeField()
    is_shown = models.BooleanField(default=True)
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    address = models.ForeignKey(Address, )


class ProductOrder(models.Model):
    parent_product = models.ForeignKey(SubProduct, on_delete=models.PROTECT)
    parent_order = models.ForeignKey(Order, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.PROTECT, null=True, blank=True)
    is_shown = models.BooleanField(default=True)


class DeliveryProvider(models.Model):
    name = models.CharField(max_length=100)
    is_shown = models.BooleanField(default=True)


class Shipment(models.Model):
    delivery_provider = models.ForeignKey(DeliveryProvider, on_delete=models.CASCADE)
    content = models.ManyToManyField(ProductOrder)
    tracking_id = models.CharField(max_length=30, null=True)
    is_shown = models.BooleanField(default=True)









