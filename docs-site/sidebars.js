/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docs: [
    'intro',
    'quickstart',
    'how-to-identify-a-facebook-url',
    'facebook-context',
    {
      type: 'category',
      label: 'Models',
      collapsed: false,
      link: { type: 'generated-index', title: 'Models' },
      items: [
        'models/profile',
        'models/post-base',
        'models/post',
        'models/media-post',
        'models/comment',
        'models/group',
        'models/marketplace-listing',
        'models/photo',
        'models/video',
        'models/animated-image',
        'models/external-link',
        'models/sticker',
        'models/group-member',
        'models/reactor',
        'models/seller',
        'models/partner-seller',
      ],
    },
    'search-engine',
    'paginated-iterator',
    'exceptions',
  ],
};

export default sidebars;