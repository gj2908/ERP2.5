from django.http import HttpResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

def export_to_excel(student_classes, class_obj):
    """
    Utility function to export student data to Excel format.
    """
    try:
        import xlwt
    except ImportError:
        return None, "Excel export functionality is not available. Please install xlwt package."

    try:
        # Create workbook and worksheet
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet(f'Class {class_obj.section} Students')
        
        # Styling
        header_style = xlwt.easyxf('font: bold on; pattern: pattern solid, fore_colour gray25;')
        
        # Add headers
        headers = ['Registration Number', 'Name', 'Email', 'Gender', 'Address', 'Parents Email']
        for col, header in enumerate(headers):
            ws.write(0, col, header, header_style)
            ws.col(col).width = 256 * 20  # Set column width
        
        # Add data
        for row, student_class in enumerate(student_classes, 1):
            student = student_class.student
            data = [
                student.registration_number,
                f"{student.admin.first_name} {student.admin.last_name}",
                student.admin.email,
                student.gender,
                student.address,
                student.parents_email
            ]
            for col, value in enumerate(data):
                ws.write(row, col, str(value) if value else '')
        
        # Create response
        response = HttpResponse(content_type='application/vnd.ms-excel')
        filename = f'class_{class_obj.section}_students.xls'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        wb.save(response)
        return response, None
        
    except Exception as e:
        return None, f"Error creating Excel file: {str(e)}"

def export_to_pdf(student_classes, class_obj):
    """
    Utility function to export student data to PDF format.
    """
    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter, landscape
        from reportlab.lib.units import inch
    except ImportError:
        return None, "PDF export functionality is not available. Please install reportlab package."

    try:
        # Create the response object
        response = HttpResponse(content_type='application/pdf')
        filename = f'class_{class_obj.section}_students.pdf'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Create the PDF object
        c = canvas.Canvas(response, pagesize=landscape(letter))
        width, height = landscape(letter)
        
        # Title
        c.setFont("Helvetica-Bold", 16)
        title = f"Students List - Class {class_obj.section}"
        c.drawString(inch, height - inch, title)
        
        # Headers
        headers = ['Reg. Number', 'Name', 'Email', 'Gender', 'Address', 'Parents Email']
        x_positions = [inch, 2.5*inch, 4*inch, 6*inch, 7*inch, 8.5*inch]
        
        c.setFont("Helvetica-Bold", 12)
        for i, header in enumerate(headers):
            c.drawString(x_positions[i], height - 2*inch, header)
        
        # Data
        c.setFont("Helvetica", 10)
        y_position = height - 2.5*inch
        for student_class in student_classes:
            if y_position < 2*inch:  # Start new page if near bottom
                c.showPage()
                c.setFont("Helvetica", 10)
                y_position = height - 2*inch
            
            student = student_class.student
            data = [
                student.registration_number,
                f"{student.admin.first_name} {student.admin.last_name}",
                student.admin.email,
                student.gender,
                student.address,
                student.parents_email
            ]
            
            for i, value in enumerate(data):
                if value:  # Only draw if value exists
                    # Truncate long strings
                    text = str(value)
                    if len(text) > 30 and i not in [0, 3]:  # Don't truncate reg number and gender
                        text = text[:27] + "..."
                    c.drawString(x_positions[i], y_position, text)
            
            y_position -= 20
        
        c.save()
        return response, None
        
    except Exception as e:
        return None, f"Error creating PDF file: {str(e)}" 