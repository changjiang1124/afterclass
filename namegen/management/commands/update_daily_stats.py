from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from django.db.models import Count
from namegen.models import PageVisitStatistics, DailyStatistics
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('namegen.management')

class Command(BaseCommand):
    help = 'Update daily statistics for namegen app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Specific date to update (YYYY-MM-DD format). Defaults to yesterday.'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Number of days to update (backwards from date). Default is 1.'
        )

    def handle(self, *args, **options):
        # Determine the date range to update
        if options['date']:
            try:
                end_date = datetime.strptime(options['date'], '%Y-%m-%d').date()
            except ValueError:
                self.stdout.write(
                    self.style.ERROR('Invalid date format. Use YYYY-MM-DD.')
                )
                return
        else:
            # Default to yesterday
            end_date = timezone.now().date() - timedelta(days=1)
        
        start_date = end_date - timedelta(days=options['days'] - 1)
        
        self.stdout.write(
            f'Updating daily statistics from {start_date} to {end_date}...'
        )
        
        # Update statistics for each day
        for i in range(options['days']):
            current_date = start_date + timedelta(days=i)
            self.update_daily_stats(current_date)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully updated daily statistics for {options["days"]} day(s)'
            )
        )

    def update_daily_stats(self, date):
        """Update daily statistics for a specific date"""
        try:
            with transaction.atomic():
                # Get or create daily statistics record
                daily_stats, created = DailyStatistics.objects.get_or_create(
                    date=date,
                    defaults={
                        'page_visits': 0,
                        'unique_visitors': 0,
                        'unique_ips': 0,
                        'name_generations': 0,
                        'name_card_generations': 0,
                        'tts_requests': 0,
                        'share_clicks': 0,
                        'country_stats': {},
                        'city_stats': {},
                    }
                )
                
                # Filter statistics for the specific date
                date_stats = PageVisitStatistics.objects.filter(
                    created_at__date=date
                )
                
                # Count different activity types
                activity_counts = date_stats.values('activity_type').annotate(
                    count=Count('id')
                )
                
                # Update counters
                for activity in activity_counts:
                    activity_type = activity['activity_type']
                    count = activity['count']
                    
                    if activity_type == 'page_visit':
                        daily_stats.page_visits = count
                    elif activity_type == 'name_generation':
                        daily_stats.name_generations = count
                    elif activity_type == 'name_card_generation':
                        daily_stats.name_card_generations = count
                    elif activity_type == 'tts_request':
                        daily_stats.tts_requests = count
                    elif activity_type == 'share_click':
                        daily_stats.share_clicks = count
                
                # Update unique visitors and IPs
                daily_stats.unique_visitors = date_stats.filter(
                    activity_type='page_visit'
                ).values('session_key').distinct().count()
                
                daily_stats.unique_ips = date_stats.values('ip_address').distinct().count()
                
                # Update geographic statistics
                country_stats = {}
                city_stats = {}
                
                for stat in date_stats:
                    if stat.country:
                        country_stats[stat.country] = country_stats.get(stat.country, 0) + 1
                    if stat.city:
                        city_stats[stat.city] = city_stats.get(stat.city, 0) + 1
                
                daily_stats.country_stats = country_stats
                daily_stats.city_stats = city_stats
                
                daily_stats.save()
                
                action = "Created" if created else "Updated"
                self.stdout.write(
                    f'  {action} statistics for {date}: '
                    f'{daily_stats.page_visits} visits, '
                    f'{daily_stats.unique_visitors} unique visitors, '
                    f'{daily_stats.name_generations} name generations'
                )
                
                logger.info(f'{action} daily statistics for {date}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error updating statistics for {date}: {str(e)}')
            )
            logger.error(f'Error updating daily statistics for {date}: {str(e)}')
    
    def cleanup_old_statistics(self, days_to_keep=90):
        """Clean up old detailed statistics (optional)"""
        cutoff_date = timezone.now().date() - timedelta(days=days_to_keep)
        
        old_stats = PageVisitStatistics.objects.filter(
            created_at__date__lt=cutoff_date
        )
        
        count = old_stats.count()
        if count > 0:
            old_stats.delete()
            self.stdout.write(
                f'Cleaned up {count} old statistics records (older than {days_to_keep} days)'
            )
            logger.info(f'Cleaned up {count} old statistics records') 