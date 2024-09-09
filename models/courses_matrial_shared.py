from  odoo import  api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.addons.http_routing.models.ir_http import slug
class CourseMatrialShared(models.Model):
    _inherit = "slide.channel"
    new_content_ids = fields.One2many('mbi.course_content', 'channel_id', string = 'Matrials', copy=True)

    @api.depends('semester', 'name')
    def get_students_counts(self):
        for r in self:
            if r.semester and r.id:
                student_ids = self.env['mbi.student'].with_context(active_test=False).search(
                    [('program_detail_ids.semester.id', '=', r.semester.id)])
                # r.students_ids= student_ids.filtered(lambda s:r.id in s.program_detail_ids.courses.ids).ids or[(5, 0, 0)]
                students_ids = student_ids.filtered(lambda s: r.id in s.program_detail_ids.courses.ids)
                if students_ids:
                    r.students_ids = [(6, 0, students_ids.ids)]

                else:
                    r.students_ids = [(5, 0, 0)]
                r.students_count = len(r.students_ids)
        # self.create_slide_partner_shared()
    @api.depends('new_content_ids','new_content_ids.is_published')

    def _compute_new_content_ids(self):
        for r in self:
            ## print("herrree",r.new_content_ids)
            for content in r.new_content_ids:
                ## print("content.name",content.name.name)
                ## print("content.id",r.id)
                content.name.channels_ids=[(4,r.id)]

    # bad
    base_domain=[
        '&', '&', ('website_id', 'in', (False, 1)), '&', ('channel_id', '=', 46), ('is_category', '=', False), '|', (
        'website_published', '=', True), ('user_id', '=', 1474)]
    # good
    base_domain=['&', '&', ('website_id', 'in', (False, 1)), '|', '&', ('channel_published_ids', 'in', [231]), (
    'is_category', '=', False), '&', ('channel_id', '=', 231), ('is_category', '=', False), '|', (
    'website_published', '=', True), ('user_id', '=', 1474)]
    # TODO still base domain needed to be fixed
    def _get_categorized_slides(self, base_domain, order, force_void=True, limit=False, offset=False):
        ## print("in _get_categorized_slides")
        """ Return an ordered structure of slides by categories within a given
        base_domain that must fulfill slides. As a course structure is based on
        its slides sequences, uncategorized slides must have the lowest sequences.

        Example
          * category 1 (sequence 1), category 2 (sequence 3)
          * slide 1 (sequence 0), slide 2 (sequence 2)
          * course structure is: slide 1, category 1, slide 2, category 2
            * slide 1 is uncategorized,
            * category 1 has one slide : Slide 2
            * category 2 is empty.

        Backend and frontend ordering is the same, uncategorized first. It
        eases resequencing based on DOM / displayed order, notably when
        drag n drop is involved. """
        self.ensure_one()
        # this line is modified by adding channel_ids
        ## print("base_domain", base_domain)
        ## print("id", self.id)
        if len(self.slide_ids):
            all_categories = self.env['slide.slide'].sudo().search([('is_category', '=', True),('channel_id', '=', self.id)])
        # newly added
        elif len(self.new_content_ids):
            all_categories = self.env['slide.slide'].sudo().search(
                [('is_category', '=', True), ("channels_ids", 'in', [self.id])])
        else:
            all_categories = self.env['slide.slide'].sudo().search(
                [('is_category', '=', True), ('channel_id', '=', self.id)])
        # print("all_categories", all_categories)
        all_slides = self.env['slide.slide'].sudo().search(base_domain, order=order)
        # print("all_slides", all_slides)
        category_data = []

        # Prepare all categories by natural order
        for category in all_categories:
            ## print("category", category.name)


            if len(self.new_content_ids) and not self.slide_ids:
                # print("self.id",self.id)
                # print("slide.channel_published_ids.ids",all_slides.filtered(lambda slide: slide.category_id == category  ))
                # slide.channel_published_ids.ids in [self.id]
                category_slides = all_slides.filtered(lambda slide: slide.category_id == category and self.id in slide.channel_published_ids.ids)
                # for s in category_slides:
                #     print(s.id,s.channel_published_ids.ids)



            else:
                category_slides = all_slides.filtered(lambda slide: slide.category_id == category)
            # print("category_slides", category_slides)
            if not category_slides and not force_void:
                continue
            category_data.append({
                'category': category, 'id': category.id,
                'name': category.name, 'slug_name': slug(category),
                'total_slides': len(category_slides),
                'slides': category_slides[(offset or 0):(limit + offset or len(category_slides))],
            })
            # print("caregoty_data",{
            #     'category': category, 'id': category.id,
            #     'name': category.name, 'slug_name': slug(category),
            #     'total_slides': len(category_slides),
            #     'slides': category_slides[(offset or 0):(limit + offset or len(category_slides))],
            # })
        if  len(self.new_content_ids) and not self.slide_ids:
        # Add uncategorized slides in first position
            uncategorized_slides = all_slides.filtered(lambda slide: not slide.category_id and self.id in slide.channel_published_ids.ids)
        else:
            uncategorized_slides = all_slides.filtered(lambda slide: not slide.category_id )
        # print("uncategorized_slides",uncategorized_slides)
        if uncategorized_slides or force_void:
            category_data.insert(0, {
                'category': False, 'id': False,
                'name': _('Uncategorized'), 'slug_name': _('Uncategorized'),
                'total_slides': len(uncategorized_slides),
                'slides': uncategorized_slides[(offset or 0):(offset + limit or len(uncategorized_slides))],
            })
        # print("category_data before return",category_data)
        return category_data


    def content_to_shared_content(self):
        for r in self:
            if len(r.slide_ids):
                vals_created=[]
                for slide in r.slide_ids:
                    vals_created.append({
                    'channel_id':r.id,
                    'name':slide.id,
                    'is_category':slide.is_category,
                    'sequence':slide.sequence,




                    })
                vals=self.env['mbi.course_content'].create(vals_created)
                # print("vals",vals)

    # @api.onchange('students_ids','new_content_ids')
    # @api.depends('students_ids','new_content_ids')
    def create_slide_partner_shared(self):
        print("hereee")

        for r in self:
            created_partners = []
            SlidePartner=self.env["slide.slide.partner"].sudo()

            for content in r.new_content_ids:
                search_slide = SlidePartner.search(
                    [("slide_id", '=', content.name.id),('channel_id', '=', content.channel_id.id)])
                if search_slide:
                    search_slide_partner=search_slide.mapped("partner_id").ids
                else:
                    search_slide=False
                    search_slide_partner=False
                # print("search_slide",search_slide)
                # print("search_slide channel_id",r.id)
                slide_partner=self.env['slide.channel.partner'].sudo().search([('channel_id', '=', r.id)])
                # print("slide_partner",slide_partner)
                partner_ids=[]
                if slide_partner:
                    partner_ids=slide_partner.mapped("partner_id")
                    # print("partner_ids", partner_ids)

                for partner in partner_ids:
                    # print("r.partner_ids",r.partner_ids)
                    # print("partner_id",partner)
                    if  (search_slide_partner and partner.id not in  search_slide_partner )or not search_slide_partner:

                        created_partners.append({
                            "slide_id": content.name.id,
                            "partner_id": partner.id,
                            "content_id": content.id,
                            "channel_id" :r.id
                        })
                # print("created_partners",created_partners)
                res=SlidePartner.create(
                    created_partners
                )
                # print("res_read",res.read())


    # def compute_category_and_slide_ids(self):
    #     self._compute_category_and_slide_ids()
    @api.depends('slide_ids.is_category')
    @api.depends('slide_ids.new_content_id.is_category')
    def _compute_category_and_slide_ids(self):
        for channel in self:

            if len(channel.slide_ids):
                channel.slide_category_ids = channel.slide_ids.filtered(lambda slide: slide.is_category)
                channel.slide_content_ids = channel.slide_ids - channel.slide_category_ids

            elif channel.new_content_ids:
                channel.slide_category_ids=channel.new_content_ids.filtered(lambda x:x.is_published).mapped('name').filtered(lambda slide:slide.is_category and slide.is_published)
                channel.slide_content_ids = channel.new_content_ids.filtered(lambda x:x.is_published).mapped('name').filtered(lambda  slide:not slide.is_category and slide.is_published)

                # print("in new _compute_category_and_slide_ids", channel.slide_content_ids)
