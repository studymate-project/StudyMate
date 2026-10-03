import Badge from '../common/Badge'

function TagList({ tags, className = '' }) {
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {tags.map((tag) => (
        <Badge key={typeof tag === 'string' ? tag : tag.label} variant={typeof tag === 'string' ? 'outline' : tag.variant}>
          {typeof tag === 'string' ? `#${tag}` : tag.label}
        </Badge>
      ))}
    </div>
  )
}

export default TagList
