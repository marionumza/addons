
{
    'name': 'Theme Caitlin',
    'category': 'Theme/eCommerce',
    'summary': 'Theme Caitlin is Odoo Multipurpose Theme '
               'with Modern style, Extremely customizable, Clean and Fully Responsive.',
    'description': 'Theme Caitlin is Odoo Multipurpose Theme '
                   'with Modern style, Extremely customizable, Clean and Fully Responsive.',
    'version': '12.0.1.0.0',
    'author': 'Tecspek',
    'data': [
        'views/assets.xml',
        'views/mid_header.xml',
        'views/customize_template.xml',
        'views/blog_carousel.xml',
        'views/about_us.xml',
        'views/services_template.xml',
        'views/marketing_plan_service.xml',
        'views/financial_analysis_service.xml',
        'views/about_us_1.xml',
        'views/about_us_2.xml',
        'views/contact_us_1.xml',
        'views/contact_us_2.xml',
        'views/contact_us_3.xml',
        'views/website_blog.xml',
        # =============Snippets============
        'snippets/s_coffee_homepage.xml',
        'snippets/s_corporate_homepage.xml',
        'snippets/s_education_homepage.xml',
        'snippets/s_medical_homepage.xml',
        'snippets/s_organic_vegetable_homepage.xml',

    ],
    'depends': [
        'mass_mailing',
        'website_blog',
        'website_crm',
        # ================================================================ #
        # TecSpek Extra Addons
        # ================================================================ #
        # 'tecspek_customize_theme'
    ],
    'demo': [
        'data/homepage.xml',
        'data/footer.xml',
        'data/menu.xml',
        'data/blog_post_demo.xml',
        'data/coffee_homepage.xml',
        'data/medical_homepage.xml',
        'data/education_homepage.xml',
        'data/organic_vegetable_homepage.xml',
    ],
    'images': [
        'static/description/main.png',
        'static/description/full_screenshot.png',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'OPL-1',
    'price': 99,
    'currency': 'EUR',
    'live_test_url': 'http://159.65.4.139:4098/r/Mtu',
}
