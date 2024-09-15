from odoo import fields, models, api
from odoo.exceptions import ValidationError


class Admission(models.Model):
    _inherit = "mbi.admission"

    def admission_confirm(self):
        student_program_id = super(Admission, self).admission_confirm()

        program_courses = student_program_id.courses
        # contents = []
        for course in program_courses:
            course.get_students_counts()
            course.create_slide_partner_shared()
            #
            # try:

                # SlidePartner = self.env["slide.slide.partner"].sudo()
                #
                # for content in course.new_content_ids:
                #     contents.append({
                #         "slide_id": content.name.id,
                #         "partner_id": student_program_id.student.partner_id.id,
                #         "content_id": content.id,
                #         "channel_id": course.id
                #     })
                #
            # except:
                # try:
                #     if course.course_copied_from:
                #         course.regenerate_slides_name(flag=0)
                #         SlidePartner = self.env["slide.slide.partner"].sudo()
                #         for content in self.new_content_ids:
                #             SlidePartner.create({
                #                 "slide_id": content.name.id,
                #                 "partner_id": student_program_id.student.partner_id.id,
                #                 "content_id": content.id,
                #                 "channel_id": course.id
                #             })
                # except Exception as e:
                #     raise ValidationError(
                #         "Error in admission Please check Course Name {} error is {}".format(course.name, e))
