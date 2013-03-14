class CourtType < ActiveRecord::Base
  attr_accessible :name, :old_id, :slug
  has_many :court_types_courts
  has_many :courts, :through => :court_types_courts

  extend FriendlyId
  friendly_id :name, use: [:slugged, :history]
end
