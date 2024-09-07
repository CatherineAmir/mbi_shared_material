# -*- coding: utf-8 -*-
import base64
import json
import logging
import werkzeug
import math


from odoo import http, tools, _
from odoo.addons.http_routing.models.ir_http import slug

from odoo.addons.website_slides.controllers.main import WebsiteSlides
# from .mbi.controllers.courses_sort import WebsiteSlidesMBI
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class WebsiteSlidesShared(WebsiteSlides):



    def sitemap_slide(env, rule, qs):
        print("hereee sitemap_slide")
        Channel = env['slide.channel']
        dom = sitemap_qs2dom(qs=qs, route='/slides/', field=Channel._rec_name)
        dom += env['website'].get_current_website().website_domain()
        # print("dom in sitemap_slide",dom)
        # print("qs in sitemap_slide",qs)
        for channel in Channel.search(dom):
            loc = '/slides/%s' % slug(channel)
            ## print("loc",loc)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    # TODO FIX here no slide.slide.partner
    def _get_channel_progress(self, channel, include_quiz=False):
        """ Replacement to user_progress. Both may exist in some transient state. """
        if channel.slide_ids:

            slides = request.env['slide.slide'].sudo().search([('channel_id', '=', channel.id)])
            channel_progress = dict((sid, dict()) for sid in slides.ids)
            ## print("channel_progress in normal",channel_progress)
            if not request.env.user._is_public() and channel.is_member:
                slide_partners = request.env['slide.slide.partner'].sudo().search([
                    ('channel_id', '=', channel.id),
                    ('partner_id', '=', request.env.user.partner_id.id),
                    ('slide_id', 'in', slides.ids)
                ])
                ## print("slide_partners in old", slide_partners)
                for slide_partner in slide_partners:
                    channel_progress[slide_partner.slide_id.id].update(slide_partner.read()[0])
                    if slide_partner.slide_id.question_ids:
                        gains = [slide_partner.slide_id.quiz_first_attempt_reward,
                                 slide_partner.slide_id.quiz_second_attempt_reward,
                                 slide_partner.slide_id.quiz_third_attempt_reward,
                                 slide_partner.slide_id.quiz_fourth_attempt_reward]
                        channel_progress[slide_partner.slide_id.id]['quiz_gain'] = gains[slide_partner.quiz_attempts_count] if slide_partner.quiz_attempts_count < len(gains) else gains[-1]

            if include_quiz:
                quiz_info = slides._compute_quiz_info(request.env.user.partner_id, quiz_done=False)
                for slide_id, slide_info in quiz_info.items():
                    channel_progress[slide_id].update(slide_info)
            ## print("channel_progress before retrun",channel_progress)
            return channel_progress

        elif len(channel.new_content_ids):
            ## print("channel",channel.id)
            ## print("channel",channel.name)
            # print("channel_published_ids",channel.id)
            slides = request.env['slide.slide'].sudo().search([("channel_published_ids", 'in', [channel.id])])
            ## print("slides in else progress",slides)
            channel_progress = dict((sid, dict()) for sid in slides.ids)
            ## print("channel_progress",channel_progress)
            content_ids=request.env['mbi.course_content'].sudo().search([('name','in',slides.ids),("is_published","=",True),("channel_id","=",channel.id)])
            ## print("channel_progress in new", channel_progress)
            if not request.env.user._is_public() and channel.is_member:
                ## print("partner",request.env.user.partner_id)
                ## print("slides",slides.ids)
                slide_partners = request.env['slide.slide.partner'].sudo().search([
                    ('channel_id', '=', channel.id),
                    ('partner_id', '=', request.env.user.partner_id.id),
                      ('slide_id', 'in', slides.ids),
                ])
                    # ("content_id","in",content_ids.ids)
                    # ('channel_id_2', '=', channel.id),

                ## print("slide_partners in new", slide_partners)
                for slide_partner in slide_partners:
                    channel_progress[slide_partner.slide_id.id].update(slide_partner.read()[0])
                    if slide_partner.slide_id.question_ids:
                        gains = [slide_partner.slide_id.quiz_first_attempt_reward,
                                 slide_partner.slide_id.quiz_second_attempt_reward,
                                 slide_partner.slide_id.quiz_third_attempt_reward,
                                 slide_partner.slide_id.quiz_fourth_attempt_reward]
                        channel_progress[slide_partner.slide_id.id]['quiz_gain'] = gains[
                            slide_partner.quiz_attempts_count] if slide_partner.quiz_attempts_count < len(gains) else \
                        gains[-1]

            if include_quiz:
                quiz_info = slides._compute_quiz_info(request.env.user.partner_id, quiz_done=False)
                for slide_id, slide_info in quiz_info.items():
                    channel_progress[slide_id].update(slide_info)
            ## print("before chnanel_progress_return", channel_progress)
            return channel_progress


    def _get_channel_slides_base_domain(self, channel):
        print("in _get_channel_slides_base_domain",channel)
        """ base domain when fetching slide list data related to a given channel

         * website related domain, and restricted to the channel and is not a
           category slide (behavior is different from classic slide);
         * if publisher: everything is ok;
         * if not publisher but has user: either slide is published, either
           current user is the one that uploaded it;
         * if not publisher and public: published;
        """
        if channel.new_content_ids:
            ## print("channel",channel)
            ## print("c.new_content_ids",channel.new_content_ids)
            slides=channel.new_content_ids.sudo().filtered(lambda x:x.is_published).mapped('name')
            ## print("slides", slides)
            channels=slides.sudo().filtered(lambda x:x.is_published).mapped('channel_id').ids
            ## print('channels',channels)
            channels.append(channel.id)
            ## print("channels", channels)
        else:
            channels=[channel.id]
        ## print("channels", channels)
        base_domain = expression.AND([request.website.website_domain(), ['&', ('channel_id', 'in',channels), ('is_category', '=', False)]])
        if not channel.can_publish:
            if request.website.is_public_user():
                base_domain = expression.AND([base_domain, [('website_published', '=', True)]])
            else:
                base_domain = expression.AND([base_domain, ['|', ('website_published', '=', True), ('user_id', '=', request.env.user.id)]])
        return base_domain

    @http.route([
        '/slides/<model("slide.channel"):channel>',
        '/slides/<model("slide.channel"):channel>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>',
        '/slides/<model("slide.channel"):channel>/tag/<model("slide.tag"):tag>/page/<int:page>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.slide"):category>',
        '/slides/<model("slide.channel"):channel>/category/<model("slide.slide"):category>/page/<int:page>',
    ], type='http', auth="public", website=True, sitemap=sitemap_slide)
    def channel(self, channel, category=None, tag=None, page=1, slide_type=None, uncategorized=False, sorting=None, search=None, **kw):
        """
        Will return all necessary data to display the requested slide_channel along with a possible category.
        """
        if not channel.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        domain = self._get_channel_slides_base_domain(channel)
        ## print("in def channel customise",domain)
        pager_url = "/slides/%s" % (channel.id)
        pager_args = {}
        slide_types = dict(request.env['slide.slide']._fields['slide_type']._description_selection(request.env))
        # print("slide_types",slide_types)
        if search:
            domain += [
                '|', '|',
                ('name', 'ilike', search),
                ('description', 'ilike', search),
                ('html_content', 'ilike', search)]
            pager_args['search'] = search
        else:
            if category:
                domain += [('category_id', '=', category.id)]
                pager_url += "/category/%s" % category.id
            elif tag:
                domain += [('tag_ids.id', '=', tag.id)]
                pager_url += "/tag/%s" % tag.id
            if uncategorized:
                domain += [('category_id', '=', False)]
                pager_args['uncategorized'] = 1
            elif slide_type:
                domain += [('slide_type', '=', slide_type)]
                pager_url += "?slide_type=%s" % slide_type

        # sorting criterion
        if channel.channel_type == 'documentation':
            default_sorting = 'latest' if channel.promote_strategy in ['specific', 'none', False] else channel.promote_strategy
            actual_sorting = sorting if sorting and sorting in request.env['slide.slide']._order_by_strategy else default_sorting
        else:
            actual_sorting = 'sequence'
        order = request.env['slide.slide']._order_by_strategy[actual_sorting]
        pager_args['sorting'] = actual_sorting
        # print("len(domain)", len(domain))
        if len(domain) == 5:
            domain.insert(-3, "|")
            domain += ['&', ("channels_ids", 'in', [channel.id]), ('is_category', '=', False)]

        else:

            domain.insert(3,'|')
            domain.insert(4,'&')
            domain.insert(5,("channel_published_ids", 'in', [channel.id]))
            domain.insert(6,('is_category', '=', False))



            # domain.insert(-3, "|")
            # domain += ['&', ("channels_ids", 'in', [channel.id]), ('is_category', '=', False)]
            # print("user id is >>>> exist")



        # print("len(domain)",len(domain)) # 5 in case of backend
        # print("domain before search count this domain include channel id", domain)
        # domain.insert(-3,"|")
        # domain+=['&',("channels_ids", 'in', [channel.id]),('is_category','=',False)]
        ## print("domain before search count this domain include channel id", domain)
        slide_count = request.env['slide.slide'].sudo().search_count(domain)
        # print("slide count",slide_count)
        page_count = math.ceil(slide_count / self._slides_per_page)
        pager = request.website.pager(url=pager_url, total=slide_count, page=page,
                                      step=self._slides_per_page, url_args=pager_args,
                                      scope=page_count if page_count < self._pager_max_pages else self._pager_max_pages)

        query_string = None
        if category:
            query_string = "?search_category=%s" % category.id
        elif tag:
            query_string = "?search_tag=%s" % tag.id
        elif slide_type:
            query_string = "?search_slide_type=%s" % slide_type
        elif uncategorized:
            query_string = "?search_uncategorized=1"

        values = {
            'channel': channel,
            'main_object': channel,
            'active_tab': kw.get('active_tab', 'home'),
            # search
            'search_category': category,
            'search_tag': tag,
            'search_slide_type': slide_type,
            'search_uncategorized': uncategorized,
            'query_string': query_string,
            'slide_types': slide_types,
            'sorting': actual_sorting,
            'search': search,
            # chatter
            'rating_avg': channel.rating_avg,
            'rating_count': channel.rating_count,
            # display data
            'user': request.env.user,
            'pager': pager,
            'is_public_user': request.website.is_public_user(),
            # display upload modal
            'enable_slide_upload': 'enable_slide_upload' in kw,
        }
        # print("values",values)
        if not request.env.user._is_public():
            last_message = request.env['mail.message'].search([
                ('model', '=', channel._name),
                ('res_id', '=', channel.id),
                ('author_id', '=', request.env.user.partner_id.id),
                ('message_type', '=', 'comment'),
                ('is_internal', '=', False)
            ], order='write_date DESC', limit=1)
            if last_message:
                last_message_values = last_message.read(['body', 'rating_value', 'attachment_ids'])[0]
                last_message_attachment_ids = last_message_values.pop('attachment_ids', [])
                if last_message_attachment_ids:
                    # use sudo as portal user cannot read access_token, necessary for updating attachments
                    # through frontend chatter -> access is already granted and limited to current user message
                    last_message_attachment_ids = json.dumps(
                        request.env['ir.attachment'].sudo().browse(last_message_attachment_ids).read(
                            ['id', 'name', 'mimetype', 'file_size', 'access_token']
                        )
                    )
            else:
                last_message_values = {}
                last_message_attachment_ids = []
            values.update({
                'last_message_id': last_message_values.get('id'),
                'last_message': tools.html2plaintext(last_message_values.get('body', '')),
                'last_rating_value': last_message_values.get('rating_value'),
                'last_message_attachment_ids': last_message_attachment_ids,
            })
            if channel.can_review:
                values.update({
                    'message_post_hash': channel._sign_token(request.env.user.partner_id.id),
                    'message_post_pid': request.env.user.partner_id.id,
                })

        # fetch slides and handle uncategorized slides; done as sudo because we want to display all
        # of them but unreachable ones won't be clickable (+ slide controller will crash anyway)
        # documentation mode may display less slides than content by category but overhead of
        # computation is reasonable
        if channel.promote_strategy == 'specific':
            values['slide_promoted'] = channel.sudo().promoted_slide_id
        else:
            values['slide_promoted'] = request.env['slide.slide'].sudo().search(domain, limit=1, order=order)

        limit_category_data = False
        if channel.channel_type == 'documentation':
            if category or uncategorized:
                limit_category_data = self._slides_per_page
            else:
                limit_category_data = self._slides_per_category
        ## print("domain before get categoriized_slide",domain)
        values['category_data'] = channel._get_categorized_slides(
            domain, order,
            force_void=not category,
            limit=limit_category_data,
            offset=pager['offset'])
        ## print("values['category_data']",values['category_data'])
        values['channel_progress'] = self._get_channel_progress(channel, include_quiz=True)
        # print("values['channel_progress']", values['channel_progress'])
        # for sys admins: prepare data to install directly modules from eLearning when
        # uploading slides. Currently supporting only survey, because why not.
        if request.env.user.has_group('base.group_system'):
            module = request.env.ref('base.module_survey')
            if module.state != 'installed':
                values['modules_to_install'] = [{
                    'id': module.id,
                    'name': module.shortdesc,
                    'motivational': _('Evaluate and certify your students.'),
                }]
        print("values before prepare additional values the end",values)
        values = self._prepare_additional_channel_values(values, **kw)
        print("values  after", values)
        return request.render('website_slides.course_main', values)

    # SLIDE.CHANNEL UTILS
    #

    @http.route([
                "/slides/slide/<model('slide.slide'):slide>",
                # "/slides/slide/<model('slide.slide'):channel>/<model('slide.slide'):slide>",
                #  "/slides/slide/558?channel=3501-235&fullscreen=1"
                 "/slides/slide/<model('slide.slide'):slide>/channel=<model('slide.channel'):channel>"],
                  type='http', auth="public", website=True,methods=["GET"],
                sitemap=True)
    def slide_view(self, slide ,**kwargs):
        print("in slide view custom",slide,kwargs)

        if "channel" in kwargs:
            # channel=int(kwargs['channel'].split('-')[1])
            # channel_id=request.env['slide.channel'].sudo().search([("id",'=',channel)])
            channel_id=kwargs['channel']
            print("channel_id in slide_view",channel_id)
        else:
            channel_id=slide.channel_id

        if not channel_id.can_access_from_current_website() or not slide.active:
            raise werkzeug.exceptions.NotFound()
        # redirection to channel's homepage for category slides
        ## print("channel_id", channel_id)
        if slide.is_category:
            return werkzeug.utils.redirect(channel_id.website_url)
        # todo fix

        self._set_viewed_slide(slide)



        values = self._get_slide_detail(slide,channel_id=channel_id)
        print("values1 set slide detail", values)
        # quiz-specific: update with karma and quiz information
        if slide.question_ids:
            values.update(self._get_slide_quiz_data(slide))
        # sidebar: update with user channel progress
        values['channel_progress'] = self._get_channel_progress(channel_id, include_quiz=True)
        print("values of progress",values)
        # Allows to have breadcrumb for the previously used filter
        values.update({
            'search_category': slide.category_id if kwargs.get('search_category') else None,
            'search_tag': request.env['slide.tag'].browse(int(kwargs.get('search_tag'))) if kwargs.get(
                'search_tag') else None,
            'slide_types': dict(
                request.env['slide.slide']._fields['slide_type']._description_selection(request.env)) if kwargs.get(
                'search_slide_type') else None,
            'search_slide_type': kwargs.get('search_slide_type'),
            'search_uncategorized': kwargs.get('search_uncategorized')
        })

        values['channel'] = channel_id
        values = self._prepare_additional_channel_values(values, **kwargs)
        values['channel'] = channel_id
        ## print("values before pop", values)
        # values.pop('channel', None)
        ## print("values after pop", values)

        values['signup_allowed'] = request.env['res.users'].sudo()._get_signup_invitation_scope() == 'b2c'

        if kwargs.get('fullscreen') == '1':
            ## print("values in full screen", values)
            return request.render("website_slides.slide_fullscreen", values)
        ## print("values in not screen", values)
        return request.render("website_slides.slide_main", values)

# TODO
    def _get_slide_detail(self, slide,channel_id=None):
        print("in get slide detail",slide,channel_id)
        if len(slide.course_content_shared_ids) and  channel_id:
            channel_id=channel_id
            print("channel_id in if",channel_id)
            base_domain = self._get_channel_slides_base_domain(channel_id)
            if len(base_domain) == 5:
                base_domain.insert(-3, "|")
                base_domain += ['&', ("channels_ids", 'in', [channel_id.id]), ('is_category', '=', False)]

            else:
                ## print("channel_id in else", channel_id)


                base_domain.insert(3, '|')
                base_domain.insert(4, '&')
                base_domain.insert(5, ("channel_published_ids", 'in', [channel_id.id]))
                base_domain.insert(6, ('is_category', '=', False))

            ## print("base_domain",base_domain)
            ## print("len(domain)",len(base_domain))
        else:
            channel_id = slide.channel_id

            base_domain = self._get_channel_slides_base_domain(slide.channel_id)
        if slide.channel_id.channel_type == 'documentation':
            related_domain = expression.AND([base_domain, [('category_id', '=', slide.category_id.id)]])

            most_viewed_slides = request.env['slide.slide'].search(base_domain, limit=self._slides_per_aside,
                                                                   order='total_views desc')
            related_slides = request.env['slide.slide'].search(related_domain, limit=self._slides_per_aside)
            category_data = []
            uncategorized_slides = request.env['slide.slide']
        else:
            ## print("base_domian in before get_categroy",base_domain)
            most_viewed_slides, related_slides = request.env['slide.slide'], request.env['slide.slide']
            category_data = channel_id._get_categorized_slides(
                base_domain, order=request.env['slide.slide']._order_by_strategy['sequence'],
                force_void=True)
            # temporarily kept for fullscreen, to remove asap
            uncategorized_domain = expression.AND(
                [base_domain, [('channel_id', '=', channel_id.id), ('category_id', '=', False)]])
            ## print("uncategorized_domain",uncategorized_domain)
            uncategorized_slides = request.env['slide.slide'].search(uncategorized_domain)
        # old
        # if  channel_id.slide_ids:
        # channel_id.compute_category_and_slide_ids()
        ## print("old",slide)
        channel_slides_ids = channel_id.slide_content_ids.ids
        ## print("channel_slides_ids",channel_slides_ids)
        slide_index = channel_slides_ids.index(slide.id)
        ## print("slide_index",slide_index)
        previous_slide = channel_id.slide_content_ids[slide_index - 1] if slide_index > 0 else None
        next_slide = channel_id.slide_content_ids[slide_index + 1] if slide_index < len(
            channel_slides_ids) - 1  else None
        ## print("previous_slide",previous_slide)
        ## print("next_slide",next_slide)
    # else:
    #
    #     print("channel_id in get slide details",channel_id)
    #
    #     channel_content_ids=channel_id.new_content_ids.filtered(lambda x:x.is_published)
    #     channel_slides = channel_content_ids.mapped("name")
    #     # if channel_slides:
    #     channel_slides_ids=channel_slides.ids
    #     print("channel_slides_ids",channel_content_ids)
    #     print("channel_slides_ids", channel_slides)
    #     slide_index = channel_slides_ids.index(slide.id)
    #     previous_slide = channel_slides[slide_index - 1] if slide_index > 0 else None
    #     next_slide =channel_slides[slide_index + 1] if slide_index < len(
    #                 channel_slides_ids) - 1  else None

        values = {
            # slide
            'slide': slide,
            'main_object': slide,
            'most_viewed_slides': most_viewed_slides,
            'related_slides': related_slides,
            'previous_slide': previous_slide,
            'next_slide': next_slide,
            'uncategorized_slides': uncategorized_slides,
            'category_data': category_data,
            # user
            'user': request.env.user,
            'is_public_user': request.website.is_public_user(),
            # rating and comments
            'comments': slide.website_message_ids or [],
        }

        # allow rating and comments
        if slide.channel_id.allow_comment:
            values.update({
                'message_post_pid': request.env.user.partner_id.id,
            })

        return values
    # tOdo
    # channel_id to be added for get_slide_detail
    @http.route('/slides/embed/<int:slide_id>/<int:channel_id>', type='http', auth='public', website=True, sitemap=False)
    def slides_embed(self, slide_id,channel_id=None ,page="1", **kw):
        # Note : don't use the 'model' in the route (use 'slide_id'), otherwise if public cannot access the embedded
        # slide, the error will be the website.403 page instead of the one of the website_slides.embed_slide.
        # Do not forget the rendering here will be displayed in the embedded iframe
        print("channel_id", channel_id)
        print("kw", kw)
        # determine if it is embedded from external web page
        referrer_url = request.httprequest.headers.get('Referer', '')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        is_embedded = referrer_url and not bool(base_url in referrer_url) or False
        # try accessing slide, and display to corresponding template
        try:
            slide = request.env['slide.slide'].browse(slide_id)
            channel = request.env['slide.channel'].browse(channel_id)
            if is_embedded:
                request.env['slide.embed'].sudo()._add_embed_url(slide.id, referrer_url)
            values = self._get_slide_detail(slide,)
            values['page'] = page
            values['is_embedded'] = is_embedded
            self._set_viewed_slide(slide)
            return request.render('website_slides.embed_slide', values)
        except AccessError:  # TODO : please, make it clean one day, or find another secure way to detect
            # if the slide can be embedded, and properly display the error message.
            return request.render('website_slides.embed_slide_forbidden', {})

    @http.route('/slides/slide/set_completed', website=True, type="json", auth="public")
    def slide_set_completed(self, slide_id):
        ## print("slide_set_completed",)
        if request.website.is_public_user():
            return {'error': 'public_user'}
        fetch_res = self._fetch_slide(slide_id)
        if fetch_res.get('error'):
            return fetch_res
        self._set_completed_slide(fetch_res['slide'])
        return {
            'channel_completion': fetch_res['slide'].channel_id.completion
        }

    @http.route('/slides/slide/<model("slide.slide"):slide>/channel=<model("slide.channel"):channel>/set_completed', website=True, type="http", auth="user")
    def slide_set_completed_and_redirect(self, slide, channel,next_slide_id=None):
        ## print("slide_set_completed_and_redirect")
        self._set_completed_slide(slide)
        next_slide = None
        ## print("channel",channel)
        if next_slide_id:
            next_slide = self._fetch_slide(next_slide_id).get('slide', None)
        return werkzeug.utils.redirect("/slides/slide/%s/channel=%s" % (slug(next_slide) if next_slide else slug(slide),slug(channel)))

    def _fetch_slide(self, slide_id):
        # print("in fetch_slide", slide_id)
        slide = request.env['slide.slide'].browse(int(slide_id)).exists()
        if not slide:
            print("here no slidde")
            return {'error': 'slide_wrong'}
        try:
            print("in try read")
            slide.check_access_rights('read')
            slide.check_access_rule('read')

        except AccessError as e:
            print("e",e)
            return {'error': 'slide_access'}
        return {'slide': slide}
    def _set_completed_slide(self, slide):
        # quiz use their specific mechanism to be marked as done
        if slide.slide_type == 'quiz' or slide.question_ids:
            raise UserError(_("Slide with questions must be marked as done when submitting all good answers "))
        if slide.website_published and slide.channel_id.is_member:
            slide.action_set_completed()
        return True