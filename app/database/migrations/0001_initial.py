import django.db.models.deletion
import pgvector.django.vector
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='NewsSource',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('url', models.URLField()),
                ('source_type', models.CharField(choices=[('rss', 'RSS Feed'), ('api', 'News API')], max_length=10)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_article_url', models.URLField(blank=True, max_length=2000, null=True)),
                ('last_checked_at', models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='ProcessingLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_name', models.CharField(max_length=100)),
                ('status', models.CharField(max_length=20)),
                ('message', models.TextField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=1000)),
                ('content', models.TextField()),
                ('url', models.URLField(unique=True)),
                ('published_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('embedding', pgvector.django.vector.VectorField(blank=True, dimensions=384, null=True)),
                ('cluster_id', models.IntegerField(blank=True, db_index=True, null=True)),
                ('is_processed', models.BooleanField(default=False)),
                ('source', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='articles', to='database.newssource')),
            ],
            options={
                'indexes': [models.Index(fields=['published_at'], name='database_ar_publish_b8757d_idx')],
            },
        ),
    ]
