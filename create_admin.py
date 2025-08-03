import logging
from app.database import SessionLocal
from app.models import User, News, Article
from app.security import get_password_hash

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    """
    Seeds the database with an admin user and sample content if it doesn't exist.
    """
    db = SessionLocal()
    try:
        # 1. Create Admin User
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.info("Admin user not found, creating one...")
            admin_user = User(
                username="admin",
                email="admin@example.com",
                hashed_password=get_password_hash("1234"),
                is_admin=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            logger.info("Admin user 'admin' with password '1234' created successfully.")
        else:
            logger.info("Admin user already exists.")

        # Clear existing news and articles to ensure fresh data
        db.query(News).delete()
        db.query(Article).delete()
        db.commit()
        logger.info("Cleared existing news and articles.")


        # 2. Create Sample News
        logger.info("Creating sample news...")
        news_items = [
            News(
                title="رویداد بزرگ علمی در راه است",
                summary="بزرگترین رویداد علمی سال با حضور دانشمندان برجسته از سراسر جهان برگزار خواهد شد.",
                content="این رویداد که هر ساله برگزار می‌شود، امسال میزبان بیش از ۱۰۰ سخنران کلیدی و هزاران شرکت‌کننده از رشته‌های مختلف علمی خواهد بود. موضوعات اصلی شامل هوش مصنوعی، بیوتکنولوژی و علوم فضایی است.",
                image_url="https://images.unsplash.com/photo-1581093458791-9a6685a3c2a6?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60",
                category="رویدادها",
                published=True,
                owner_id=admin_user.id
            ),
            News(
                title="کشف جدید در حوزه پزشکی",
                summary="محققان موفق به شناسایی یک روش نوین برای درمان بیماری‌های قلبی شدند.",
                content="این روش که بر پایه سلول‌های بنیادی است، نتایج بسیار امیدوارکننده‌ای در آزمایشات اولیه نشان داده و می‌تواند انقلابی در درمان بیماری‌های قلبی-عروقی ایجاد کند.",
                image_url="https://images.unsplash.com/photo-1576091160550-2173dba999ab?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60",
                category="پزشکی",
                published=True,
                owner_id=admin_user.id
            ),
            News(
                title="فناوری 5G و آینده ارتباطات",
                summary="چگونه نسل پنجم شبکه‌های موبایل، دنیای ما را متحول خواهد کرد؟",
                content="فناوری 5G با سرعت بسیار بالا و تأخیر کم، امکانات جدیدی را برای اینترنت اشیاء (IoT)، خودروهای خودران و واقعیت مجازی فراهم می‌کند. در این خبر به بررسی پتانسیل‌ها و چالش‌های این فناوری می‌پردازیم.",
                image_url="https://images.unsplash.com/photo-1611003221039-9ac5a1e27447?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60",
                category="فناوری",
                published=True,
                owner_id=admin_user.id
            ),
        ]
        db.add_all(news_items)
        logger.info(f"Added {len(news_items)} sample news items.")

        # 3. Create Sample Articles
        logger.info("Creating sample articles...")
        article_items = [
            Article(
                title="کاربرد هوش مصنوعی در تحلیل داده‌های بزرگ",
                summary="این مقاله به بررسی چگونگی استفاده از الگوریتم‌های یادگیری ماشین برای تحلیل داده‌های حجیم می‌پردازد.",
                content="با افزایش حجم داده‌های تولیدی در صنایع مختلف، نیاز به ابزارهای هوشمند برای استخراج اطلاعات ارزشمند از این داده‌ها بیش از پیش احساس می‌شود. در این مقاله، الگوریتم‌های مختلفی مانند شبکه‌های عصبی عمیق و ماشین‌های بردار پشتیبان مورد بررسی قرار گرفته و مزایا و معایب هر یک شرح داده می‌شود.",
                image_url="https://images.unsplash.com/photo-1555949963-ff9fe0c870eb?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60",
                published=True,
                owner_id=admin_user.id
            ),
            Article(
                title="آینده انرژی‌های تجدیدپذیر",
                summary="چالش‌ها و فرصت‌های پیش روی توسعه انرژی‌های پاک مانند خورشیدی و بادی.",
                content="انرژی‌های تجدیدپذیر به عنوان یک راهکار کلیدی برای مقابله با تغییرات اقلیمی شناخته می‌شوند. این مقاله به بررسی آخرین فناوری‌ها در این زمینه، چالش‌های اقتصادی و سیاسی، و چشم‌انداز آینده این منابع انرژی می‌پردازد.",
                image_url="https://images.unsplash.com/photo-1497435334941-8c899ee9e8e9?ixlib=rb-1.2.1&auto=format&fit=crop&w=800&q=60",
                published=True,
                owner_id=admin_user.id
            ),
        ]
        db.add_all(article_items)
        logger.info(f"Added {len(article_items)} sample articles.")

        db.commit()
        logger.info("Database seeding complete.")

    except Exception as e:
        logger.error(f"An error occurred during database seeding: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("Starting database seeding process...")
    from app.database import create_db_and_tables
    create_db_and_tables()
    seed_database()
