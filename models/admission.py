from odoo import fields, models, api
from odoo.exceptions import ValidationError
import logging
_logger = logging.getLogger(__name__)
import time
class Admission(models.Model):
    _inherit = "mbi.admission"

    def admission_confirm(self):
        student_program_id = super(Admission, self).admission_confirm()

        program_courses = student_program_id.courses
        # contents = []
        for course in program_courses:
            try:
                course.with_context(prefetch_fields=False).students_ids = [(4, student_program_id.student.id)]
                course.regenerate_slides_name()

                course.create_slide_partner(student_program_id.student.partner_id)
            except Exception as e:
                time.sleep(3)


                try:
                    course.with_context(prefetch_fields=False).students_ids = [(4, student_program_id.student.id)]
                except Exception as e:
                    raise ValidationError("exception in course create1 {}".format(e))
                try:
                    course.regenerate_slides_name()
                except Exception as e:
                    raise ValidationError("exception in course create2 {}".format(e))
                try:
                    course.create_slide_partner(student_program_id.student.partner_id)

                except Exception as e:
                    raise ValidationError("exception in course create3 {}".format(e))
                    # time.sleep(5)
                    # try:
                    #     course.students_ids = [(4, student_program_id.student.id)]
                    #     course.regenerate_slides_name()
                    #     course.create_slide_partner(student_program_id.student.partner_id)
                    # except Exception as e:
                    #     time.sleep(7)
                    #     try:
                    #         course.students_ids = [(4, student_program_id.student.id)]
                    #         course.regenerate_slides_name()
                    #         course.create_slide_partner(student_program_id.student.partner_id)
                    #     except Exception as e:
                    #
                    #         raise ValidationError("exception in course create {}".format(e))
                    #


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
