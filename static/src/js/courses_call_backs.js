odoo.define('mbi_shared_material.slides_fullscreen', function (require) {
    'use strict'


    const FullScreen_main = require('website_slides.fullscreen');


    return FullScreen_main.include({


        _pushUrlState: function () {

            let urlParts = window.location.pathname.split('/');

            urlParts[urlParts.length - 2] = this.get('slide').slug;
            let url = urlParts.join('/');

            this.$('.o_wslides_fs_exit_fullscreen').attr('href', url);
            let params = {'fullscreen': 1};
            if (this.get('slide').isQuiz) {
                params.quiz = 1;
            }
            let fullscreenUrl = _.str.sprintf('%s?%s', url, $.param(params));

            history.pushState(null, '', fullscreenUrl);
        },

    });
});