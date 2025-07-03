from odoo import fields, models, api,_
from odoo.tools import sql
import datetime
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.http import request
from datetime import datetime
from odoo.addons.http_routing.models.ir_http import url_for
from werkzeug import urls
class SlideContentPartnerRelation(models.Model):
    _inherit = 'slide.slide.partner'

    content_id=fields.Many2one("mbi.course_content",ondelete = "cascade", index = True, required = True)
    channel_id=fields.Many2one("slide.channel",ondelete = "cascade",compute='_compute_channel_id_2',store=True)
    channel_id_2 = fields.Many2one(
        'slide.channel', string="Channel",
         store=True, index=True, ondelete='cascade',compute='_compute_channel_id_2')
    slide_id = fields.Many2one('slide.slide',store=1,compute='compute_slide_id',readonly=False)
    @api.depends('content_id','slide_id')
    def _compute_channel_id_2(self):
        for r in self:
            if r.content_id.channel_id:
                r.channel_id = r.content_id.channel_id.id
            else:
                r.channel_id =r.slide_id.channel_id.id
            if r.slide_id:
                r.channel_id_2=r.slide_id.channel_id.id


    @api.depends('content_id')
    @api.depends('content_id')
    def compute_slide_id(self):
        for r in self:
            if r.content_id:
                r.slide_id=r.content_id.name.id

    def _set_completed_callback(self):




        slide_partners=self.env['slide.channel.partner'].search([
            ('channel_id', 'in', self.channel_id.ids),
            ('partner_id', 'in', self.partner_id.ids),
        ])
        for s in slide_partners:
            s._recompute_completion()
    def _recompute_completion(self):
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            ['&', '&', ('channel_id', 'in', self.mapped('channel_id').ids),
             ('partner_id', 'in', self.mapped('partner_id').ids),
             ('completed', '=', True),
             ('content_id.is_published', '=', True),
             ('content_id.active', '=', True)],
            ['channel_id', 'partner_id'],
            groupby = ['channel_id', 'partner_id'], lazy = False)
        mapped_data = dict()
        for item in read_group_res:
            mapped_data.setdefault(item['channel_id'][0], dict())
            mapped_data[item['channel_id'][0]][item['partner_id'][0]] = item['__count']

        partner_karma = dict.fromkeys(self.mapped('partner_id').ids, 0)
        for record in self:
            record.completed_slides_count = mapped_data.get(record.channel_id.id, dict()).get(record.partner_id.id, 0)
            record.completion = 100.0 if record.completed else round(
                100.0 * record.completed_slides_count / (record.channel_id.total_slides or 1))
            if not record.completed and record.channel_id.active and record.completed_slides_count >= record.channel_id.total_slides:
                record.completed = True
                partner_karma[record.partner_id.id] += record.channel_id.karma_gen_channel_finish

        partner_karma = {partner_id: karma_to_add
                         for partner_id, karma_to_add in partner_karma.items() if karma_to_add > 0}

        if partner_karma:
            users = self.env['res.users'].sudo().search([('partner_id', 'in', list(partner_karma.keys()))])
            for user in users:
                users.add_karma(partner_karma[user.partner_id.id])




class SlideSlide(models.Model):
    _inherit = 'slide.slide'
    course_content_shared_ids=fields.One2many('mbi.course_content',"name",readonly=True)
    channels_ids = fields.Many2many('slide.channel','all_channel_ids',compute="_set_channels_ids",store=True)
    channel_published_ids = fields.Many2many('slide.channel',"published_channel",compute="_set_channels_ids",store=True)
    @api.depends('course_content_shared_ids','course_content_shared_ids.is_published')
    def _set_channels_ids(self):
        for r in self:

            if r.course_content_shared_ids:


                channel_ids_published=r.course_content_shared_ids.filtered(lambda m :m.is_published)
                if channel_ids_published:
                    r.channel_published_ids=channel_ids_published.mapped('channel_id').ids
                else:
                    r.channel_published_ids=False

                r.channels_ids=r.course_content_shared_ids.mapped('channel_id').ids

    def action_set_completed(self,channel=None):

        if channel:

            if not channel.is_member:
                raise UserError(_('You cannot mark a slide as completed if you are not among its members.'))

        else:

            if any(not slide.channel_id.is_member for slide in self):
                # print("error in set complete")
                raise UserError(_('You cannot mark a slide as completed if you are not among its members.'))
        # print("in action_set_completed no error")
        if channel.id != self.channel_id.id:
            return self.course_content_shared_ids.filtered(lambda x:x.channel_id.id==channel.id).action_set_completed_content(self.env.user.partner_id)
        else:
            return self._action_set_completed(self.env.user.partner_id)

    def _action_set_completed(self, target_partner):

        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('slide_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        existing_sudo.write({'completed': True})

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        created = SlidePartnerSudo.create([{
            'slide_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'partner_id': target_partner.id,
            'vote': 0,
            'completed': True} for new_slide in new_slides])

        return True
    def _has_additional_resources(self):
        """Sudo required for public user to know if the course has additional
        resources that they will be able to access once a member."""
        self.ensure_one()
        return bool(self.sudo().slide_resource_ids)





class CourseContent(models.Model):
    _name = 'mbi.course_content'
    _description = 'Material Related to Many Courses'
    _inherit = [
        'mail.thread',
        'image.mixin',
        'website.seo.metadata', 'website.published.mixin']
    _order_by_strategy = {
        'sequence': 'sequence asc, id asc',
        'most_viewed': 'total_views desc',
        'most_voted': 'likes desc',
        'latest': 'date_published desc',
    }
    _order = 'sequence asc, is_category asc, id asc'
    _rec_name = 'name'

    channel_id=fields.Many2one('slide.channel',auto_join=True,index=1,string="Title")
    is_published = fields.Boolean(default = False,copy=False)

    name=fields.Many2one('slide.slide',required=1,index=1,store=True)
    # name=fields.Char()
    slide_type=fields.Selection(related='name.slide_type',store=1)
    completion_time=fields.Float(related='name.completion_time',store=1)
    sequence = fields.Integer('Sequence', default = 0)  #"widget_name=handle"
    is_preview = fields.Boolean(string='Allow Preview',related='name.is_preview',store=1)
    is_category = fields.Boolean('Is a category', default = False)
    category_id = fields.Many2one('slide.slide', string = "Section", compute = "_compute_category_id", store = True)
    slide_ids = fields.One2many('slide.slide', "category_id", string = "Slides")
    active = fields.Boolean(default = True, tracking = 100)
    date_published = fields.Datetime('Publish Date', readonly = True, tracking = 1,copy=False)
    is_new_content = fields.Boolean('Is New Content', compute = '_compute_is_new_content')
    comments_count = fields.Integer('Number of comments', compute = "_compute_comments_count")
    slide_views = fields.Integer('# of Website Views', store = True, compute = "_compute_slide_views")
    public_views = fields.Integer('# of Public Views', copy = False)
    total_views = fields.Integer("Views", default = "0", compute = '_compute_total', store = True)
    channel_type = fields.Selection(related = "channel_id.channel_type", string = "Channel type")
    channel_allow_comment = fields.Boolean(related = "channel_id.allow_comment", string = "Allows comment")
    likes = fields.Integer('Likes', compute='_compute_like_info', store=True, compute_sudo=False)
    dislikes = fields.Integer('Dislikes', compute='_compute_like_info', store=True, compute_sudo=False)
    user_vote = fields.Integer('User vote', compute='_compute_user_membership_id', compute_sudo=False)
    embed_code = fields.Html('Embed Code', readonly = True, related='name.embed_code')

    datas = fields.Binary('Content', attachment = True,related='name.binary_content')
    url = fields.Char('Document URL', help = "Youtube or Google Document URL",related='name.url')
    # document_id = fields.Char('Document ID', help = "Youtube or Google Document ID",related='name.document_id')
    # link_ids = fields.One2many('slide.slide.link', 'slide_id', string = "External URL for this slide",related='name.link_ids')
    slide_resource_ids = fields.One2many('slide.slide.resource', 'slide_id',
                                         string = "Additional Resource for this slide",related='name.slide_resource_ids')
    slide_resource_downloadable = fields.Boolean('Allow Download', default = True,
                                                 help = "Allow the user to download the content of the slide.",related='name.slide_resource_downloadable')
    # mime_type = fields.Char('Mime-type',related='name.mime_type')
    html_content = fields.Html("HTML Content", help = "Custom HTML content for slides of type 'Web Page'.",
                               translate = True, sanitize_attributes = False, sanitize_form = False,related='name.html_content')
    # website
    website_id = fields.Many2one(related = 'channel_id.website_id', readonly = True)
    slide_partner_ids = fields.One2many('slide.slide.partner', 'content_id', string = 'Subscribers information',
                                        groups = 'website_slides.group_website_slides_officer', copy = False)


    auto_publish=fields.Boolean('Auto Publish', default = False,copy=False)
    datetime_publish=fields.Datetime('Datetime Published',copy=False)
    @api.model
    def auto_publish_material(self):

        this_time=lambda : datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ## print("this_time",this_time())
        ContentMaterialSUDO=self.env['mbi.course_content'].sudo()
        domain=[
            ('is_published','=',False),
            ('auto_publish','=',True),
            ("datetime_publish",'!=',False),
            ("datetime_publish",'<=',this_time(),),
            ("is_category","=",False)
        ]
        content_published=ContentMaterialSUDO.sudo().search(domain)
        # print("content_published",content_published)
        for c in content_published:

            c.is_published=True


            if c.channel_id:
                try:
                    # print("message _post")
                    c.channel_id.message_post(body="{} Marterial is Published at {}".format(c.name.name,str(this_time())))

                    # print("message _posted")
                except Exception as e:
                    pass
                    # print("exception in message post",e)



    @api.depends('slide_partner_ids.content_id')
    def _compute_slide_views(self):
        # TODO awa: tried compute_sudo, for some reason it doesn't work in here...
        read_group_res = self.env['slide.slide.partner'].sudo().read_group(
            [('content_id', 'in', self.ids)],
            ['content_id'],
            groupby = ['content_id']
        )
        mapped_data = dict((res['content_id'][0], res['content_id_count']) for res in read_group_res)
        for content in self:
            content.slide_views = mapped_data.get(content.id, 0)

    @api.depends('website_message_ids.res_id', 'website_message_ids.model', 'website_message_ids.message_type')
    def _compute_comments_count(self):
        for content in self:
            content.comments_count = len(content.website_message_ids)

    @api.depends('slide_views', 'public_views')
    def _compute_total(self):
        for record in self:
            record.total_views = record.slide_views + record.public_views

    @api.depends('slide_partner_ids.vote')
    def _compute_like_info(self):
        if not self.ids:
            self.update({'likes': 0, 'dislikes': 0})
            return
        rg_data_like = self.env['slide.slide.partner'].sudo().read_group(
            [('content_id', 'in', self.ids), ('vote', '=', 1)],
            ['content_id'], ['content_id']
        )
        rg_data_dislike = self.env['slide.slide.partner'].sudo().read_group(
            [('content_id', 'in', self.ids), ('vote', '=', -1)],
            ['content_id'], ['content_id']
        )
        mapped_data_like = dict(
            (rg_data['content_id'][0], rg_data['slide_id_count'])
            for rg_data in rg_data_like
        )
        mapped_data_dislike = dict(
            (rg_data['content_id'][0], rg_data['slide_id_count'])
            for rg_data in rg_data_dislike
        )

        for content in self:
            content.likes = mapped_data_like.get(content.id, 0)
            content.dislikes = mapped_data_dislike.get(content.id, 0)
    #
    @api.depends('slide_ids.sequence', 'slide_ids.slide_type', 'slide_ids', 'slide_ids.is_category')
    def _compute_slides_statistics(self):
        # Do not use dict.fromkeys(self.ids, dict()) otherwise it will use the same dictionnary for all keys.
        # Therefore, when updating the dict of one key, it updates the dict of all keys.
        keys = ['nbr_%s' % slide_type for slide_type in
                self.env['slide.slide']._fields['slide_type'].get_values(self.env)]
        default_vals = dict((key, 0) for key in keys + ['total_slides'])

        res = self.env['mbi.course_content'].read_group(
            [('is_published', '=', True), ('category_id', 'in', self.ids), ('is_category', '=', False)],
            ['category_id', 'slide_type'], ['category_id', 'slide_type'],
            lazy = False)

        type_stats = self._compute_slides_statistics_type(res)

        for record in self:
            record.update(type_stats.get(record._origin.id, default_vals))


    @api.onchange("is_published")
    def _onchange_is_published(self):
        for  r in self:
            r.name._set_channels_ids()

    def _compute_slides_statistics_type(self, read_group_res):
        """ Compute statistics based on all existing slide types """
        slide_types = self.env['slide.slide']._fields['slide_type'].get_values(self.env)
        keys = ['nbr_%s' % slide_type for slide_type in slide_types]
        result = dict((cid, dict((key, 0) for key in keys + ['total_slides'])) for cid in self.ids)
        for res_group in read_group_res:
            cid = res_group['category_id'][0]
            slide_type = res_group.get('slide_type')
            if slide_type:
                slide_type_count = res_group.get('__count', 0)
                result[cid]['nbr_%s' % slide_type] = slide_type_count
                result[cid]['total_slides'] += slide_type_count
        return result

    def _compute_user_membership_id(self):
        slide_partners = self.env['slide.slide.partner'].sudo().search([
            ('content_id', 'in', self.ids),
            ('partner_id', '=', self.env.user.partner_id.id),
        ])

        for record in self:
            record.user_vote = next(
                (slide_partner for slide_partner in slide_partners if slide_partner.content_id == record),
                self.env['slide.slide.partner']
            )





    # @api.onchange('channel_id')
    # def slide_domain(self):
    #     pass
    #     return{
    #         'domain':{'name':
    #             [('parent_course','=',self.channel_id.course_name.id)]}
    #     }



    @api.depends('date_published', 'is_published')
    def _compute_is_new_content(self):
        for content in self:
            content.is_new_content = content.date_published > fields.Datetime.now() - relativedelta(
                days = 7) if content.is_published else False

    @api.depends('channel_id.slide_ids.is_category', 'channel_id.slide_ids.sequence')
    def _compute_category_id(self):
        """ Will take all the slides of the channel for which the index is higher
        than the index of this category and lower than the index of the next category.

        Lists are manually sorted because when adding a new browse record order
        will not be correct as the added slide would actually end up at the
        first place no matter its sequence."""
        self.category_id = False  # initialize whatever the state

        channel_slides = {}
        for content in self:
            if content.channel_id.id not in channel_slides:
                channel_slides[content.channel_id.id] = content.channel_id.slide_ids

        for cid, slides in channel_slides.items():
            current_category = self.env['slide.slide']
            slide_list = list(slides)
            slide_list.sort(key = lambda s: (s.sequence, not s.is_category))
            for slide in slide_list:
                if slide.is_category:
                    current_category = slide
                elif slide.category_id != current_category:
                    slide.category_id = current_category.id
    @api.model
    def default_get(self, fields):
        res = super(CourseContent, self).default_get(fields)

        if 'default_channel_id' in self._context:
            res['channel_id'] = self._context.get('default_channel_id')

        return res

    @api.model
    def create(self, values):
        # Do not publish slide if user has not publisher rights
        channel = self.env['slide.channel'].browse(values['channel_id'])
        if not channel.can_publish:
            # 'website_published' is handled by mixin
            values['date_published'] = False

        if values.get('slide_type') == 'infographic' and not values.get('image_1920'):
            values['image_1920'] = values['datas']
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True
        if values.get('is_published') and not values.get('date_published'):
            values['date_published'] = datetime.now()
        if values.get('url') and not values.get('document_id'):
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)

        content = super(CourseContent, self).create(values)

        # if content.is_published and not content.is_category:
            # content._post_publication()
        content.channel_id.create_slide_partner_shared()
        return content

    def write(self, values):
        if values.get('url') and values['url'] != self.url:
            doc_data = self._parse_document_url(values['url']).get('values', dict())
            for key, value in doc_data.items():
                values.setdefault(key, value)
        if values.get('is_category'):
            values['is_preview'] = True
            values['is_published'] = True

        res = super(CourseContent, self).write(values)

        if values.get('completed'):
            self._set_completed_callback()
        if values.get('is_published'):
            self.date_published = datetime.now()
            # self._post_publication()

        if 'is_published' in values or 'active' in values:
            # if the slide is published/unpublished, recompute the completion for the partners

            self.slide_partner_ids._set_completed_callback()

        return res

    def _post_publication(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for slide in self.filtered(lambda slide: slide.website_published and slide.channel_id.publish_template_id):
            publish_template = slide.channel_id.publish_template_id
            html_body = publish_template.with_context(base_url=base_url)._render_field('body_html', slide.ids)[slide.id]
            subject = publish_template._render_field('subject', slide.ids)[slide.id]
            # We want to use the 'reply_to' of the template if set. However, `mail.message` will check
            # if the key 'reply_to' is in the kwargs before calling _get_reply_to. If the value is
            # falsy, we don't include it in the 'message_post' call.
            kwargs = {}
            reply_to = publish_template._render_field('reply_to', slide.ids)[slide.id]
            if reply_to:
                kwargs['reply_to'] = reply_to
            slide.channel_id.with_context(mail_create_nosubscribe=True).message_post(
                subject=subject,
                body=html_body,
                subtype_xmlid='website_slides.mt_channel_slide_published',
                email_layout_xmlid='mail.mail_notification_light',
                **kwargs,
            )
        return True

    def action_set_completed_content(self, target_partner):

        self_sudo = self.sudo()
        slide=self.mapped("name")
        channel=self.mapped("channel_id")

        # ('content_id', 'in', self.ids),
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([

            ('partner_id', '=', target_partner.id),
            ('slide_id','in',slide.ids),
            ("channel_id",'in',channel.ids)
        ])
        # print("existing_sudo of content_conteny", existing_sudo)
        existing_sudo.write({'completed': True})
        channel=self.mapped('channel_id')
        # print("channel", channel)
        new_slides = self_sudo - existing_sudo.mapped('content_id')
        # print("new_slides", new_slides)
        res=SlidePartnerSudo.create([{
            'channel_id_2': new_slide.name.channel_id.id,
            'channel_id': channel.id,
            'partner_id': target_partner.id,
            'slide_id':new_slide.name.id,
            'vote': 0,
            'completed': True} for new_slide in new_slides])
        # print("res_partner =",res)
        return True

    def _action_set_viewed(self, target_partner, quiz_attempts_inc=False):
        self_sudo = self.sudo()
        SlidePartnerSudo = self.env['slide.slide.partner'].sudo()
        existing_sudo = SlidePartnerSudo.search([
            ('content_id', 'in', self.ids),
            ('partner_id', '=', target_partner.id)
        ])
        if quiz_attempts_inc and existing_sudo:
            sql.increment_field_skiplock(existing_sudo, 'quiz_attempts_count')
            SlidePartnerSudo.invalidate_cache(fnames = ['quiz_attempts_count'], ids = existing_sudo.ids)

        new_slides = self_sudo - existing_sudo.mapped('slide_id')
        return SlidePartnerSudo.create([{
            'content_id': new_slide.id,
            'channel_id': new_slide.channel_id.id,
            'channel_id_2':new_slide.slide_id.channel_id.id,
            'partner_id': target_partner.id,
            'quiz_attempts_count': 1 if quiz_attempts_inc else 0,
            'vote': 0} for new_slide in new_slides])