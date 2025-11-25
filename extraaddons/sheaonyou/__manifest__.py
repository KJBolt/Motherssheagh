{
    'name': 'Sheaonyou',
    'version': '1.1',
    'sequence': 1,
    'module_type': 'official',
    'summary': 'Customization for Sheaonyou',
    'author': 'GeoIworks',
    'images': [],
    'depends': ['account', 'website', 'stock'],
    'data': [
        'views/home.xml',
        'views/contact.xml',
        'views/about.xml',
        'views/cart.xml',
        'views/shop.xml',
        'views/shop_details.xml',
        'views/remove_cart_icon.xml',
        # 'views/test.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'sheaonyou/static/src/img/*',
        ]
    },
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
