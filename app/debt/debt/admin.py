from django.contrib import admin
from debt.models import Instance, Person, Debt, SubDebt

admin.site.register(Instance)
admin.site.register(Person)
admin.site.register(Debt)
admin.site.register(SubDebt)

