import csv

from django.core.management.base import BaseCommand

from recipes.models import Ingredient

csv_file = 'ingredients.csv'
fields = ('name', 'measurement_unit')


class Command(BaseCommand):
    help = 'Импорт данных из csv файлов в БД.'

    def handle(self, *args, **options):
        print('Старт импорта ингредиентов')
        try:
            with open(
                'recipes/data/ingredients.csv',
                'r',
                encoding='utf-8',
            ) as file:
                if not file:
                    raise FileNotFoundError
                reader = csv.DictReader(file, delimiter=',')
                for row in reader:
                    Ingredient.objects.get_or_create(**row)
        except Exception as error:
            print(f'Импорт завершен с ошибкой: {error}')
        self.stdout.write(self.style.SUCCESS('Импорт завершен'))
