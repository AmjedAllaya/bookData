import scrapy
import json
from copy import deepcopy

class GoodreadsSpider(scrapy.Spider):
    name = "goodreads"
    allowed_domains = ["goodreads.com"]
    start_urls = ["https://www.goodreads.com/genres"]

    def parse(self, response):
        categories = response.css('.bigBoxBody .left a.gr-hyperlink')
        for category in categories:
            category_name = category.css('::text').get()
            category_url = category.css('::attr(href)').get()

            # Modify the URL as required
            new_category_url = category_url.replace('/genres', '/shelf/show')
            modified_url = response.urljoin(new_category_url)
            yield scrapy.Request(url=modified_url, callback=self.parse_category, meta={'category_name': category_name})

    def parse_category(self, response):
        category_name = response.meta['category_name']

        books = response.css('.elementList')

        category_data = {
            'category_name': category_name,
            'books': []
        }

        for book in books:
            book_details = {
                'title': book.css('.bookTitle::text').get(),
                'image_url': book.css('img::attr(src)').get(),
                'link': response.urljoin(book.css('.bookTitle::attr(href)').get())
            }

            # Follow the link to the book page
            yield scrapy.Request(url=book_details['link'], callback=self.parse_book, meta={'category_data': category_data, 'book_details': book_details})

    def parse_book(self, response):
        category_data = response.meta['category_data']
        book_details = response.meta['book_details']

        # Extract additional data from the book page
        contributor = response.css('.BookPageMetadataSection__contributor .ContributorLink__name::text').get()
        book_details['author'] = contributor.strip() if contributor else None

        rating_stats = response.css('.BookPageMetadataSection__ratingStats .RatingStatistics__column')
        book_details['avg_rating'] = rating_stats.css('.RatingStatistics__rating::text').get()

        # Extract ratings and reviews count
        ratings_count = rating_stats.css('span[data-testid="ratingsCount"]::text').get()
        reviews_count = rating_stats.css('span[data-testid="reviewsCount"]::text').get()

        book_details['ratings_count'] = ratings_count.strip() if ratings_count else None
        book_details['reviews_count'] = reviews_count.strip() if reviews_count else None

        # Extract Goodreads Choice Award details
        award_flag = response.css('.ChoiceAwardBadge__flag span.Text__body3::text').get()
        award_details = response.css('.ChoiceAwardBadge span.Text__body3::text').get()

        if award_flag and award_details:
            book_details['award'] = {
                'flag': award_flag.strip(),
                'details': award_details.strip()
            }
        else:
            book_details['award'] = None

        # Extract book description
        description = response.css('div[data-testid="description"] span.Formatted::text').get()
        book_details['description'] = description.strip() if description else None

        # Extract additional details
        details_section = response.css('.FeaturedDetails p[data-testid^=""]')
        for detail in details_section:
            key = detail.css('::attr(data-testid)').get()
            value = detail.css('::text').get()
            book_details[key] = value.strip() if value else None

        # Extract author details
        author_section = response.css('.PageSection h3.Text__title3:contains("About the author") + div .DetailsLayoutRightParagraph span.Formatted::text').get()
        book_details['author_details'] = author_section.strip() if author_section else None

        # Extract related books
        related_books = response.css('.DynamicCarousel__item')
        book_details['related_books'] = []

        for related_book in related_books:
            related_book_data = {
                'title': related_book.css('.BookCard__title::text').get(),
                'author': related_book.css('.BookCard__authorName::text').get(),
                'avg_rating': related_book.css('.AverageRating__ratingValue::text').get(),
                'ratings_count': related_book.css('.AverageRating__ratingsCount::text').get()
            }
            book_details['related_books'].append(related_book_data)

        # Extract ReviewsSectionStatistics details
        reviews_statistics = response.css('.ReviewsSectionStatistics__ratingStatistics .RatingStatistics__column')
        avg_rating = reviews_statistics[0].css('.RatingStatistics__rating::text').get()
        ratings_info = reviews_statistics[1].css('span::text').getall()

        book_details['avg_rating'] = avg_rating.strip() if avg_rating else None
        book_details['ratings_info'] = {
            'total_ratings': ratings_info[0].strip() if ratings_info else None,
            'total_reviews': ratings_info[1].strip() if len(ratings_info) > 1 else None
        }

        # Extract RatingsHistogram details
        histogram = response.css('.RatingsHistogram__bar')
        book_details['ratings_histogram'] = []

        for bar in histogram:
            rating = bar.css('.RatingsHistogram__labelTitle::text').get()
            count_percentage = bar.css('.RatingsHistogram__labelTotal::text').get()

            rating_data = {
                'rating': rating.strip() if rating else None,
                'count_percentage': count_percentage.strip() if count_percentage else None
            }

            book_details['ratings_histogram'].append(rating_data)

        # Deep copy the category_data to avoid reusing the same dictionary
        category_data_copy = deepcopy(category_data)
        category_data_copy['books'].append(book_details)

        # Return the deep copied category_data at the end of parsing the book
        yield category_data_copy
