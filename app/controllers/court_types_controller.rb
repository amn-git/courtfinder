class CourtTypesController < ApplicationController
  
  respond_to :html, :json

  def index
    @court_types = CourtType.order(:name)
  end

  def show
    @court_type = CourtType.find(params[:id])

    if request.path != court_type_path(@court_type, :format => params[:format])
      redirect_to court_type_path(@court_type, :format => params[:format]), status: :moved_permanently
    else
      respond_with @court_type
    end
  end
end