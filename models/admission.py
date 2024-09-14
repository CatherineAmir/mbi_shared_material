from odoo import fields, models, api


class Admission(models.Model):
    _inherit="mbi.admission"

    def admission_confirm(self):
        student_program_id=super(Admission,self).admission_confirm()

        program_courses=student_program_id.courses
        for course in program_courses:
            course.get_students_counts()
            course.create_slide_partner_shared()

