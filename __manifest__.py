# -*- coding: utf-8 -*-
{
    'name': "mbi_shared_material",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "SITA EGYPT",
    'website': "https://sita-eg.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','website_slides','mbi','website','website_profile','web_tour','web',"web_notify"],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'security/record_rules.xml',

        'views/front_end_assets.xml',
        'views/content_material.xml',
        'views/slide_channel_courses_material.xml',
        'views/slide_slide.xml',
        'views/cron_job.xml',

        'templates/shared_material.xml',
        'templates/website_template_lesson_mbi.xml',
        'templates/slides_website_channel_homepage_mbi.xml',




    ],
    # only loaded in demonstration mode

    'installable':True,
    'application':False,
    'images': ['static/description/icon.png'],
}
